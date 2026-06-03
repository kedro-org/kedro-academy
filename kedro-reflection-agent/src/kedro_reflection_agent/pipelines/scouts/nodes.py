"""Nodes for the ``scouts`` pipeline.

Five deterministic, LLM-free detectors that sit between Evaluate and Reflect.
Each detector watches for one class of failure and emits ``Signal`` records.

All detectors follow the same signature:

    detect_<name>(
        per_case_scores: list[dict],
        aggregate_scores: dict,
        eval_cases: list[dict],
        run_id: str,
        agent_id: str,
        **threshold_kwargs,
    ) -> list[Signal]

The top-level ``run_scouts`` node calls all detectors, merges their signals,
writes them to the per-run signals file, and updates the cross-agent index.

Design rules (see DESIGN.md / docs/Architecture.md):
  - Pure and deterministic.  No LLM calls, no network calls.
  - Run fast — O(n) over per_case_scores.
  - Reserve ``high`` confidence for unambiguous cases.
  - ``reason`` must be self-contained (quote threshold + observed value).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from kedro_reflection_agent.models.shared import CaseScore, Signal
from kedro_reflection_agent.pipelines._common import utc_now_iso

logger = logging.getLogger(__name__)

# Path for the rolling cross-agent signal index (read + write inside node,
# same pattern as apply_history.json in the apply pipeline).
_SIGNAL_INDEX_PATH = Path("data/outputs/signal_index.json")


# ---------------------------------------------------------------------------
# Top-level node
# ---------------------------------------------------------------------------


def run_scouts(
    per_case_scores: list[dict],
    aggregate_scores: dict,
    eval_cases: Any,
    run_id: str,
    agent_id: str,
    # score_regression thresholds
    scout_regression_delta_medium: float,
    scout_regression_delta_high: float,
    scout_regression_window: int,
    # rubric_miss threshold
    scout_rubric_miss_min_cases: int,
    # hallucination threshold
    scout_hallucination_min_cases: int,
    # tone_drift thresholds
    scout_tone_floor: float,
    scout_tone_min_cases: int,
    # cross_unit_pattern thresholds
    scout_cross_unit_min_agents: int,
    scout_cross_unit_window: int,
) -> list[dict]:
    """Run all scouts against the current run outputs and return serialised signals.

    Also updates the rolling cross-agent signal index on disk so the
    ``cross_unit_pattern`` scout and Portfolio Intelligence have history.
    """
    all_cases = [CaseScore.model_validate(c) for c in per_case_scores]
    # Drop task-error cases (email not found / generation failed).
    # These score 0.0 across the board and would swamp every scout.
    cases = [cs for cs in all_cases if not cs.output.get("error")]
    n_skipped = len(all_cases) - len(cases)
    if n_skipped:
        logger.info(
            "scouts %s (%s): skipping %d task-error cases (no email generated)",
            run_id, agent_id, n_skipped,
        )

    # Build rubric lookup from the DatasetClient — same pattern as reflection pipeline.
    rubric_by_case_id: dict[str, dict] = {}
    for item in eval_cases.items:
        rubric_by_case_id[item.id] = (item.expected_output or {}).get("rubric", {})

    signals: list[Signal] = []

    # 1. score_regression
    signals.extend(
        _detect_score_regression(
            aggregate_scores=aggregate_scores,
            run_id=run_id,
            agent_id=agent_id,
            delta_medium=scout_regression_delta_medium,
            delta_high=scout_regression_delta_high,
            window=scout_regression_window,
        )
    )

    # 2. rubric_miss
    signals.extend(
        _detect_rubric_miss(
            cases=cases,
            rubric_by_case_id=rubric_by_case_id,
            run_id=run_id,
            agent_id=agent_id,
            min_cases=scout_rubric_miss_min_cases,
        )
    )

    # 3. hallucination_flag
    signals.extend(
        _detect_hallucination(
            cases=cases,
            rubric_by_case_id=rubric_by_case_id,
            run_id=run_id,
            agent_id=agent_id,
            min_cases=scout_hallucination_min_cases,
        )
    )

    # 4. tone_drift
    signals.extend(
        _detect_tone_drift(
            cases=cases,
            run_id=run_id,
            agent_id=agent_id,
            floor=scout_tone_floor,
            min_cases=scout_tone_min_cases,
        )
    )

    # 5. cross_unit_pattern (reads + updates the rolling index)
    cross_unit_signals, updated_index = _detect_cross_unit_pattern(
        current_signals=signals,
        run_id=run_id,
        agent_id=agent_id,
        min_agents=scout_cross_unit_min_agents,
        window=scout_cross_unit_window,
    )
    signals.extend(cross_unit_signals)

    # Persist the updated cross-agent index.
    _SIGNAL_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SIGNAL_INDEX_PATH.write_text(json.dumps(updated_index, indent=2), encoding="utf-8")
    logger.info(
        "scouts %s (%s): signal_index updated to %d entries",
        run_id,
        agent_id,
        len(updated_index),
    )

    n_high = sum(1 for s in signals if s.confidence == "high")
    n_medium = sum(1 for s in signals if s.confidence == "medium")
    logger.info(
        "scouts %s (%s): %d signals total — %d high, %d medium, %d low",
        run_id,
        agent_id,
        len(signals),
        n_high,
        n_medium,
        len(signals) - n_high - n_medium,
    )

    return [s.model_dump() for s in signals]


# ---------------------------------------------------------------------------
# 1. score_regression
# ---------------------------------------------------------------------------


def _detect_score_regression(
    aggregate_scores: dict,
    run_id: str,
    agent_id: str,
    delta_medium: float,
    delta_high: float,
    window: int,
) -> list[Signal]:
    """Fire when any scored dimension drops vs the rolling average of past runs.

    Past run aggregate_scores are read from disk by scanning
    ``data/outputs/runs/*/aggregate_scores.json``, filtering to the same
    agent_id (via run_metadata.json), and sorting by started_at.
    """
    current_means: dict[str, float] = aggregate_scores.get("mean_per_scorer", {})
    if not current_means:
        return []

    past_means_by_scorer = _load_past_scorer_means(
        run_id=run_id, agent_id=agent_id, window=window
    )
    if not past_means_by_scorer:
        logger.info("score_regression: no historical runs found for %s, skipping", agent_id)
        return []

    signals: list[Signal] = []
    for scorer, current_val in current_means.items():
        past_vals = past_means_by_scorer.get(scorer)
        if not past_vals:
            continue
        rolling_avg = sum(past_vals) / len(past_vals)
        delta = rolling_avg - current_val  # positive = drop

        if delta <= 0:
            continue  # no regression

        confidence = "medium" if delta <= delta_high else "high"
        if delta < delta_medium:
            continue  # below medium threshold, ignore

        signals.append(
            Signal(
                signal_type="score_regression",
                agent_id=agent_id,
                run_id=run_id,
                confidence=confidence,
                evidence_text=(
                    f"Scorer '{scorer}': current={current_val:.3f}, "
                    f"rolling_avg={rolling_avg:.3f} over {len(past_vals)} past run(s)."
                ),
                reason=(
                    f"Drop of {delta:.3f} exceeds "
                    f"{'high' if confidence == 'high' else 'medium'} "
                    f"threshold ({delta_high if confidence == 'high' else delta_medium})."
                ),
                created_at=utc_now_iso(),
            )
        )
        logger.info(
            "score_regression [%s] %s: current=%.3f rolling=%.3f delta=%.3f → %s",
            agent_id,
            scorer,
            current_val,
            rolling_avg,
            delta,
            confidence,
        )

    return signals


def _load_past_scorer_means(
    run_id: str, agent_id: str, window: int
) -> dict[str, list[float]]:
    """Scan past run directories and return per-scorer value lists.

    Only runs matching ``agent_id`` (from run_metadata.json) and not the
    current ``run_id`` are included. Sorted by ``started_at`` ascending;
    the last ``window`` entries are kept.
    """
    runs_root = Path(f"data/{agent_id}/outputs/runs")
    if not runs_root.exists():
        return {}

    candidates: list[tuple[str, dict]] = []  # (started_at, mean_per_scorer)
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir() or run_dir.name == run_id:
            continue
        agg_path = run_dir / "aggregate_scores.json"
        if not agg_path.exists():
            continue
        agg = json.loads(agg_path.read_text())
        started_at = agg.get("started_at", "")
        candidates.append((started_at, agg.get("mean_per_scorer", {})))

    candidates.sort(key=lambda x: x[0])  # chronological order
    recent = candidates[-window:]  # keep last `window` runs

    result: dict[str, list[float]] = {}
    for _, means in recent:
        for scorer, val in means.items():
            result.setdefault(scorer, []).append(float(val))
    return result


# ---------------------------------------------------------------------------
# 2. rubric_miss
# ---------------------------------------------------------------------------


def _detect_rubric_miss(
    cases: list[CaseScore],
    rubric_by_case_id: dict[str, dict],
    run_id: str,
    agent_id: str,
    min_cases: int,
) -> list[Signal]:
    """Fire when rubric-derived checks fail on ≥ min_cases cases.

    Checks three rubric-derived heuristics already in per_case_scores:
      - ``cta_present``: expected_cta not found in body
      - ``subject_present``: subject line missing
      - ``no_fake_skus``: forbidden mention / fabricated token detected

    Also checks required_mentions from the rubric directly against email body.
    """
    signals: list[Signal] = []

    # --- heuristic-derived misses (from evaluations in per_case_scores) ---
    heuristic_checks = ["cta_present", "subject_present", "no_fake_skus"]
    for check_name in heuristic_checks:
        failing_cases = []
        for cs in cases:
            val_by_name = {e.name: e for e in cs.evaluations}
            ev = val_by_name.get(check_name)
            if ev and ev.value == 0.0:
                failing_cases.append((cs.case_id, ev.comment or ""))

        if len(failing_cases) >= min_cases:
            evidence = "; ".join(
                f"{cid}: {comment[:120]}" for cid, comment in failing_cases[:5]
            )
            signals.append(
                Signal(
                    signal_type="rubric_miss",
                    agent_id=agent_id,
                    run_id=run_id,
                    confidence="high",
                    evidence_text=f"Check '{check_name}' failed on {len(failing_cases)} cases: {evidence}",
                    reason=(
                        f"'{check_name}' scored 0.0 on {len(failing_cases)} cases "
                        f"(threshold: ≥{min_cases})."
                    ),
                    created_at=utc_now_iso(),
                )
            )
            logger.info(
                "rubric_miss [%s] %s: failed on %d/%d cases",
                agent_id, check_name, len(failing_cases), len(cases),
            )

    # --- required_mentions check (from rubric in eval_cases) ---
    required_miss_by_mention: dict[str, list[str]] = {}
    for cs in cases:
        body = (cs.output.get("body") or "").lower()
        rubric = rubric_by_case_id.get(cs.case_id, {})
        for mention in rubric.get("required_mentions", []):
            if mention.lower() not in body:
                required_miss_by_mention.setdefault(mention, []).append(cs.case_id)

    for mention, case_ids in required_miss_by_mention.items():
        if len(case_ids) >= min_cases:
            signals.append(
                Signal(
                    signal_type="rubric_miss",
                    agent_id=agent_id,
                    run_id=run_id,
                    confidence="high",
                    evidence_text=(
                        f"Required mention '{mention}' absent in {len(case_ids)} cases: "
                        f"{', '.join(case_ids[:5])}"
                    ),
                    reason=(
                        f"required_mention '{mention}' missing in {len(case_ids)} cases "
                        f"(threshold: ≥{min_cases})."
                    ),
                    created_at=utc_now_iso(),
                )
            )
            logger.info(
                "rubric_miss [%s] required_mention '%s': absent in %d/%d cases",
                agent_id, mention, len(case_ids), len(cases),
            )

    return signals


# ---------------------------------------------------------------------------
# 3. hallucination_flag
# ---------------------------------------------------------------------------


def _detect_hallucination(
    cases: list[CaseScore],
    rubric_by_case_id: dict[str, dict],
    run_id: str,
    agent_id: str,
    min_cases: int,
) -> list[Signal]:
    """Fire when fabricated content is detected on ≥ min_cases cases.

    Two checks:
      - ``no_fake_skus == 0.0``: the heuristic evaluator found a SKU-shaped
        token outside known product names (already computed during evaluation).
      - forbidden_mentions present in body (from rubric).
    """
    signals: list[Signal] = []

    # Check 1: no_fake_skus heuristic
    fake_sku_cases = []
    for cs in cases:
        val_by_name = {e.name: e for e in cs.evaluations}
        ev = val_by_name.get("no_fake_skus")
        if ev and ev.value == 0.0:
            fake_sku_cases.append((cs.case_id, ev.comment or ""))

    if len(fake_sku_cases) >= min_cases:
        evidence = "; ".join(
            f"{cid}: {comment[:200]}" for cid, comment in fake_sku_cases[:5]
        )
        signals.append(
            Signal(
                signal_type="hallucination_flag",
                agent_id=agent_id,
                run_id=run_id,
                confidence="high",
                evidence_text=f"Fabricated SKU tokens in {len(fake_sku_cases)} cases: {evidence}",
                reason=(
                    f"no_fake_skus scored 0.0 on {len(fake_sku_cases)} cases "
                    f"(threshold: ≥{min_cases})."
                ),
                created_at=utc_now_iso(),
            )
        )

    # Check 2: forbidden_mentions in body
    forbidden_hits: dict[str, list[str]] = {}  # mention → case_ids
    for cs in cases:
        body = (cs.output.get("body") or "").lower()
        rubric = rubric_by_case_id.get(cs.case_id, {})
        for mention in rubric.get("forbidden_mentions", []):
            if mention.lower() in body:
                forbidden_hits.setdefault(mention, []).append(cs.case_id)

    for mention, case_ids in forbidden_hits.items():
        if len(case_ids) >= min_cases:
            signals.append(
                Signal(
                    signal_type="hallucination_flag",
                    agent_id=agent_id,
                    run_id=run_id,
                    confidence="high",
                    evidence_text=(
                        f"Forbidden mention '{mention}' found in {len(case_ids)} cases: "
                        f"{', '.join(case_ids[:5])}"
                    ),
                    reason=(
                        f"forbidden_mention '{mention}' present in {len(case_ids)} cases "
                        f"(threshold: ≥{min_cases})."
                    ),
                    created_at=utc_now_iso(),
                )
            )
            logger.info(
                "hallucination_flag [%s] forbidden '%s' in %d/%d cases",
                agent_id, mention, len(case_ids), len(cases),
            )

    if not signals:
        logger.info("hallucination_flag [%s]: no hallucinations detected", agent_id)
    return signals


# ---------------------------------------------------------------------------
# 4. tone_drift
# ---------------------------------------------------------------------------

# Per-agent tone/quality dimensions to monitor.  Maps agent_id → list of
# scorer names treated as tone/quality proxies.  Falls back to the B2B set.
_TONE_DIMENSIONS: dict[str, list[str]] = {
    "b2b_sales": ["writing_quality", "personalization", "groundedness"],
    "consumer_mktg": ["offer_relevance", "personalisation", "urgency_cta", "tone", "compliance"],
    "customer_care": ["empathy_opener", "resolution_clarity", "tone", "compliance", "escalation_avoidance"],
}
_TONE_DIMENSIONS_DEFAULT = ["writing_quality", "personalization", "groundedness"]


def _detect_tone_drift(
    cases: list[CaseScore],
    run_id: str,
    agent_id: str,
    floor: float,
    min_cases: int,
) -> list[Signal]:
    """Fire when a tone/quality dimension falls below floor for ≥ min_cases cases.

    Cases are processed in case_id order for deterministic consecutive counting.
    """
    signals: list[Signal] = []
    tone_dims = _TONE_DIMENSIONS.get(agent_id, _TONE_DIMENSIONS_DEFAULT)
    sorted_cases = sorted(cases, key=lambda cs: cs.case_id)

    for dim in tone_dims:
        below: list[tuple[str, float]] = []  # (case_id, value) below floor
        for cs in sorted_cases:
            val_by_name = {e.name: e.value for e in cs.evaluations}
            val = val_by_name.get(dim)
            if val is not None and val < floor:
                below.append((cs.case_id, val))

        if len(below) >= min_cases:
            evidence_parts = [f"{cid}={val:.2f}" for cid, val in below[:8]]
            signals.append(
                Signal(
                    signal_type="tone_drift",
                    agent_id=agent_id,
                    run_id=run_id,
                    confidence="medium",
                    evidence_text=(
                        f"Dimension '{dim}' below floor ({floor}) on "
                        f"{len(below)} cases: {', '.join(evidence_parts)}"
                    ),
                    reason=(
                        f"'{dim}' < {floor} on {len(below)} cases "
                        f"(threshold: ≥{min_cases} cases below floor)."
                    ),
                    created_at=utc_now_iso(),
                )
            )
            logger.info(
                "tone_drift [%s] %s: below %.2f on %d/%d cases",
                agent_id, dim, floor, len(below), len(sorted_cases),
            )

    if not signals:
        logger.info("tone_drift [%s]: no drift detected", agent_id)
    return signals


# ---------------------------------------------------------------------------
# 5. cross_unit_pattern
# ---------------------------------------------------------------------------


def _detect_cross_unit_pattern(
    current_signals: list[Signal],
    run_id: str,
    agent_id: str,
    min_agents: int,
    window: int,
) -> tuple[list[Signal], list[dict]]:
    """Fire when the same signal_type appears in ≥ min_agents distinct agents.

    Reads and updates the rolling cross-agent signal index at
    ``data/outputs/signal_index.json``.  The index is a list of records:
      {signal_type, agent_id, run_id, created_at}

    Returns (new_signals, updated_index).
    """
    # Load existing index.
    index: list[dict] = _load_signal_index()

    # Append records for each signal fired in this run.
    new_entries = [
        {
            "signal_type": s.signal_type,
            "agent_id": s.agent_id,
            "run_id": s.run_id,
            "created_at": s.created_at,
        }
        for s in current_signals
    ]
    index.extend(new_entries)

    # Keep only the last `window` entries total to bound growth.
    index = index[-window * 10 :]  # generous cap: window × 10 entries

    # Check for cross-unit patterns within the rolling window.
    window_entries = index[-window:]
    # Group by signal_type → set of distinct agent_ids
    agents_by_type: dict[str, set[str]] = {}
    for entry in window_entries:
        agents_by_type.setdefault(entry["signal_type"], set()).add(entry["agent_id"])

    cross_unit_signals: list[Signal] = []
    for signal_type, agents_seen in agents_by_type.items():
        if agent_id not in agents_seen:
            continue  # this agent isn't part of the pattern
        if len(agents_seen) < min_agents:
            continue  # not enough agents
        agents_list = sorted(agents_seen)
        cross_unit_signals.append(
            Signal(
                signal_type="cross_unit_pattern",
                agent_id=agent_id,
                run_id=run_id,
                confidence="high",
                evidence_text=(
                    f"Signal type '{signal_type}' detected across {len(agents_seen)} agents: "
                    f"{', '.join(agents_list)} — within last {window} index entries."
                ),
                reason=(
                    f"'{signal_type}' appears in {len(agents_seen)} agents "
                    f"(threshold: ≥{min_agents})."
                ),
                created_at=utc_now_iso(),
            )
        )
        logger.info(
            "cross_unit_pattern [%s]: '%s' detected in %d agents — %s",
            agent_id,
            signal_type,
            len(agents_seen),
            agents_list,
        )

    return cross_unit_signals, index


def _load_signal_index() -> list[dict]:
    if _SIGNAL_INDEX_PATH.exists():
        return json.loads(_SIGNAL_INDEX_PATH.read_text())
    return []
