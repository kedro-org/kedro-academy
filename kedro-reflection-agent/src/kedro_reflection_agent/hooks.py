"""Kedro project hooks.

RunIndexHook (for poc)
──────────────────────
Observes pipeline completions and upserts a RunIndexEntry into
data/outputs/run_index.json after each relevant pipeline:

  campaign   → creates the entry: identity, config snapshot, run stats
  evaluation → upserts: quality scores, Langfuse links, delta vs previous run
  scouts     → upserts: signal summary
  reflection → upserts: reflection_id
  apply      → upserts: reflection_applied, applied_at

No changes to pipeline or node code required.

NoSQL migration: replace _load_index / _save_index with db driver calls.
The RunIndexEntry model and all hook logic remain identical.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from kedro.framework.hooks import hook_impl

from kedro_reflection_agent.utils.paths import RUN_INDEX_PATH

from .models.shared import RunIndexEntry

logger = logging.getLogger(__name__)

# Maps a sentinel node name (unique per pipeline) to the pipeline identifier.
_SENTINEL_NODE_TO_PIPELINE: dict[str, str] = {
    "generate_emails_node": "campaign",
    "run_experiment_node": "evaluation",
    "run_scouts_node": "scouts",
    "reflect_node": "reflection",
    "commit_reflection_node": "apply",
}


def _pipeline_name_from_nodes(node_names: set[str]) -> str:
    for sentinel, name in _SENTINEL_NODE_TO_PIPELINE.items():
        if sentinel in node_names:
            return name
    return ""


# ---------------------------------------------------------------------------
# Index persistence helpers  (swap these two for NoSQL migration)
# ---------------------------------------------------------------------------

def _load_index() -> list[dict]:
    if RUN_INDEX_PATH.exists():
        return json.loads(RUN_INDEX_PATH.read_text(encoding="utf-8"))
    return []


def _save_index(records: list[dict]) -> None:
    RUN_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_INDEX_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")


def _upsert(run_id: str, agent_id: str, updates: dict) -> None:
    """Merge `updates` into the existing entry for (run_id, agent_id), or append a new one."""
    records = _load_index()
    for i, r in enumerate(records):
        if r.get("run_id") == run_id and r.get("agent_id") == agent_id:
            records[i] = {**r, **updates}
            _save_index(records)
            return
    # New entry — append
    records.append(updates)
    _save_index(records)


def _run_id_for_reflection(agent_id: str, reflection_id: str) -> str | None:
    """Return run_id for the run whose reflection step produced reflection_id."""
    for record in reversed(_load_index()):
        if (
            record.get("agent_id") == agent_id
            and record.get("reflection_id") == reflection_id
        ):
            return record.get("run_id")
    return None


# ---------------------------------------------------------------------------
# Hook
# ---------------------------------------------------------------------------

class RunIndexHook:
    """Append-only run index written as a side-effect of each pipeline."""

    @hook_impl
    def after_pipeline_run(
        self,
        run_params: dict[str, Any],
        pipeline: Any,
        catalog: Any,
    ) -> None:
        node_names = {n.name for n in pipeline.nodes}
        pipeline_name: str = _pipeline_name_from_nodes(node_names)
        params: dict = run_params.get("runtime_params") or {}
        run_id: str | None = params.get("run_id")
        agent_id: str | None = params.get("agent_id")
        reflection_id: str | None = params.get("reflection_id")

        if not agent_id:
            return

        if pipeline_name == "apply":
            if not run_id and reflection_id:
                run_id = _run_id_for_reflection(agent_id, reflection_id)
            if not run_id:
                return
        elif not run_id:
            return  # pipeline run without our params (e.g. kedro viz)

        try:
            if pipeline_name == "campaign":
                self._after_campaign(run_id, agent_id, catalog)
            elif pipeline_name == "evaluation":
                self._after_evaluation(run_id, agent_id, catalog, params)
            elif pipeline_name == "scouts":
                self._after_scouts(run_id, agent_id, catalog)
            elif pipeline_name == "reflection":
                if reflection_id:
                    _upsert(run_id, agent_id, {"reflection_id": reflection_id})
            elif pipeline_name == "apply":
                self._after_apply(run_id, agent_id, catalog, reflection_id)
        except Exception:
            logger.exception(
                "RunIndexHook: failed to update run_index for %s/%s — skipping",
                agent_id, run_id,
            )

    # ── per-pipeline handlers ────────────────────────────────────────────────

    def _after_campaign(self, run_id: str, agent_id: str, catalog: Any) -> None:
        run_meta: dict = catalog.load("run_metadata")

        prompt_snapshot = _read_text(
            Path("data") / agent_id / "campaign" / "prompts" / "system_prompt.json"
        )
        skill_snapshot = _read_text(
            Path("data") / agent_id / "campaign" / "skills" / f"{agent_id}_style.md"
        )

        started_at = run_meta.get("started_at", "")
        finished_at = run_meta.get("finished_at", "")
        duration = _iso_delta_seconds(started_at, finished_at)

        index = _load_index()
        run_seq = sum(1 for r in index if r.get("agent_id") == agent_id) + 1

        entry = RunIndexEntry(
            run_id=run_id,
            agent_id=agent_id,
            run_seq=run_seq,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration,
            status="partial" if run_meta.get("n_errors", 0) == run_meta.get("n_cases", 1) else "completed",
            model_name=run_meta.get("model_name", ""),
            prompt_name=f"{agent_id}-system-prompt",
            prompt_version=run_meta.get("prompt_version"),
            prompt_snapshot=prompt_snapshot,
            skill_snapshot=skill_snapshot,
            n_cases=run_meta.get("n_cases", 0),
            n_outputs=run_meta.get("n_emails", 0),
            n_errors=run_meta.get("n_errors", 0),
        )
        _upsert(run_id, agent_id, entry.model_dump())
        logger.info("RunIndexHook: campaign entry written for %s/%s (seq=%d)", agent_id, run_id, run_seq)

    def _after_evaluation(
        self, run_id: str, agent_id: str, catalog: Any, params: dict
    ) -> None:
        agg: dict = catalog.load("aggregate_scores")

        # Compute delta vs the most recent completed run for this agent.
        index = _load_index()
        prev = _latest_completed(index, agent_id, exclude_run_id=run_id)
        delta_mean = delta_pass = None
        if prev and prev.get("mean_score") is not None and agg.get("mean_total") is not None:
            delta_mean = round(agg["mean_total"] - prev["mean_score"], 4)
        if prev and prev.get("pass_rate") is not None and agg.get("pass_rate") is not None:
            delta_pass = round(agg["pass_rate"] - prev["pass_rate"], 4)

        _upsert(run_id, agent_id, {
            "pass_rate": agg.get("pass_rate"),
            "mean_score": agg.get("mean_total"),
            "mean_per_scorer": agg.get("mean_per_scorer"),
            "passing_threshold": agg.get("passing_threshold"),
            "judge_model_name": agg.get("judge_model_name"),
            "judge_prompt_version": agg.get("judge_prompt_version"),
            "langfuse_experiment_url": agg.get("dataset_run_url"),
            "langfuse_dataset_run_id": agg.get("dataset_run_id"),
            "prev_run_id": prev.get("run_id") if prev else None,
            "delta_mean_score": delta_mean,
            "delta_pass_rate": delta_pass,
        })
        logger.info(
            "RunIndexHook: evaluation scores upserted for %s/%s (pass_rate=%.2f, delta=%.3f)",
            agent_id, run_id,
            agg.get("pass_rate", 0),
            delta_mean or 0,
        )

    def _after_scouts(self, run_id: str, agent_id: str, catalog: Any) -> None:
        signals: list[dict] = catalog.load("signals")
        by_conf: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        types: list[str] = []
        for s in signals:
            conf = s.get("confidence", "low")
            by_conf[conf] = by_conf.get(conf, 0) + 1
            st = s.get("signal_type", "")
            if st and st not in types:
                types.append(st)

        _upsert(run_id, agent_id, {
            "n_signals": len(signals),
            "signal_types": types,
            "signals_by_confidence": by_conf,
        })
        logger.info(
            "RunIndexHook: scouts upserted for %s/%s (%d signals)", agent_id, run_id, len(signals)
        )

    def _after_apply(
        self,
        run_id: str,
        agent_id: str,
        catalog: Any,
        reflection_id: str | None = None,
    ) -> None:
        history: list[dict] = catalog.load("apply_history")
        matching = [
            row for row in history
            if row.get("agent_id") == agent_id
            and (not reflection_id or row.get("reflection_id") == reflection_id)
        ]
        if not matching:
            return
        latest = matching[-1]
        _upsert(run_id, agent_id, {
            "reflection_applied": True,
            "applied_at": latest.get("applied_at"),
            "applied_by": latest.get("applied_by"),
        })
        logger.info("RunIndexHook: apply event upserted for %s/%s", agent_id, run_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _iso_delta_seconds(start: str, end: str) -> float:
    try:
        from datetime import datetime, timezone
        fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if "." in start else "%Y-%m-%dT%H:%M:%S%z"
        t0 = datetime.fromisoformat(start.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return round((t1 - t0).total_seconds(), 1)
    except Exception:
        return 0.0


def _latest_completed(
    index: list[dict], agent_id: str, exclude_run_id: str
) -> dict | None:
    candidates = [
        r for r in index
        if r.get("agent_id") == agent_id
        and r.get("run_id") != exclude_run_id
        and r.get("mean_score") is not None
    ]
    return candidates[-1] if candidates else None
