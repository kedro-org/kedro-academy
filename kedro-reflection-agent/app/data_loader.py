"""Data loader functions for the Reflection Hub dashboard.

All functions read from disk. They never throw — missing files return
sensible empty defaults so the UI can render gracefully before any
pipelines have run.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from kedro_reflection_agent.utils.paths import APPLY_HISTORY_PATH, RUN_INDEX_PATH, SIGNAL_INDEX_PATH

_ROOT = Path(__file__).parent.parent
_DATA = _ROOT / "data"


def _read_json(path: Path) -> Any:
    """Read JSON file; return None if missing or invalid."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


# ── Agent registry ───────────────────────────────────────────────────────────

def get_agent_ids() -> list[str]:
    return ["b2b_sales", "consumer_mktg", "customer_care"]


# ── Run index ─────────────────────────────────────────────────────────────────

def get_run_index() -> list[dict]:
    """Read the global run index (``RUN_INDEX_PATH``)."""
    data = _read_json(_ROOT / RUN_INDEX_PATH)
    if isinstance(data, list):
        return data
    return []


def get_runs_for_agent(agent_id: str) -> list[str]:
    """Return sorted list of run directory names for *agent_id*."""
    runs_dir = _DATA / agent_id / "outputs" / "runs"
    if not runs_dir.is_dir():
        return []
    dirs = sorted(p.name for p in runs_dir.iterdir() if p.is_dir())
    return dirs


# ── Run-level artifacts ───────────────────────────────────────────────────────

def get_aggregate_scores(agent_id: str, run_id: str) -> dict | None:
    """Read aggregate_scores.json for a specific agent run.

    The run data lives at data/{agent_id}/outputs/runs/{run_id}/
    but we also fall back to data/outputs/runs/{run_id}/ for backward compat.
    """
    primary = _DATA / agent_id / "outputs" / "runs" / run_id / "aggregate_scores.json"
    fallback = _DATA / "outputs" / "runs" / run_id / "aggregate_scores.json"
    data = _read_json(primary) or _read_json(fallback)
    if isinstance(data, dict):
        return data
    return None


def get_per_case_scores(agent_id: str, run_id: str) -> list[dict]:
    primary = _DATA / agent_id / "outputs" / "runs" / run_id / "per_case_scores.json"
    fallback = _DATA / "outputs" / "runs" / run_id / "per_case_scores.json"
    data = _read_json(primary) or _read_json(fallback)
    if isinstance(data, list):
        return data
    return []


def get_signals(agent_id: str, run_id: str) -> list[dict]:
    primary = _DATA / agent_id / "outputs" / "runs" / run_id / "signals.json"
    fallback = _DATA / "outputs" / "runs" / run_id / "signals.json"
    for path in (primary, fallback):
        data = _read_json(path)
        if isinstance(data, list):
            return data
    # Also look in the global signal_index, filtered by agent+run
    signal_index = _read_json(_ROOT / SIGNAL_INDEX_PATH)
    if isinstance(signal_index, list):
        return [s for s in signal_index if s.get("run_id") == run_id and s.get("agent_id") == agent_id]
    return []


def get_emails(agent_id: str, run_id: str) -> dict[str, dict]:
    """Return emails dict keyed by case_id (filename stem)."""
    emails_dir = _DATA / agent_id / "outputs" / "runs" / run_id / "emails"
    result: dict[str, dict] = {}
    if emails_dir.is_dir():
        for f in sorted(emails_dir.glob("*.json")):
            data = _read_json(f)
            if isinstance(data, dict):
                result[f.stem] = data
    # Fallback path
    emails_dir2 = _DATA / "outputs" / "runs" / run_id / "emails"
    if emails_dir2.is_dir() and not result:
        for f in sorted(emails_dir2.glob("*.json")):
            data = _read_json(f)
            if isinstance(data, dict):
                result[f.stem] = data
    return result


# ── Seed data ─────────────────────────────────────────────────────────────────

def get_targets(agent_id: str) -> list[dict]:
    data = _read_json(_DATA / agent_id / "seed" / "targets.json")
    if isinstance(data, list):
        return data
    return []


# ── Reflection artifacts ──────────────────────────────────────────────────────

def get_reflection_summary(agent_id: str, reflection_id: str) -> str:
    path = _DATA / agent_id / "outputs" / "reflections" / reflection_id / "summary.md"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    return ""


def get_proposed_prompt(agent_id: str, reflection_id: str) -> list[dict]:
    path = _DATA / agent_id / "outputs" / "reflections" / reflection_id / "proposed_prompt.json"
    data = _read_json(path)
    if isinstance(data, list):
        return data
    return []


def get_proposed_skill(agent_id: str, reflection_id: str) -> str:
    path = _DATA / agent_id / "outputs" / "reflections" / reflection_id / "proposed_skill.md"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    return ""


# ── Apply history ─────────────────────────────────────────────────────────────

def get_apply_history() -> list[dict]:
    data = _read_json(_ROOT / APPLY_HISTORY_PATH)
    if isinstance(data, list):
        return data
    return []


# ── Campaign assets ───────────────────────────────────────────────────────────

def get_system_prompt(agent_id: str) -> list[dict]:
    data = _read_json(_DATA / agent_id / "campaign" / "prompts" / "system_prompt.json")
    if isinstance(data, list):
        return data
    return []


def get_skill_text(agent_id: str) -> str:
    path = _DATA / agent_id / "campaign" / "skills" / f"{agent_id}_style.md"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    return ""


# ── Convenience helpers ───────────────────────────────────────────────────────

_RUN_ID_RE = re.compile(r"^(.+?)(\d+)$")
_REFL_ID_RE = re.compile(r"^refl_(\d+)$")


def next_run_id(run_id: str | None, *, default: str = "run_1") -> str:
    """Return the next sequential run_id (``run_2`` → ``run_3``). ``None`` → *default*."""
    if not run_id:
        return default
    match = _RUN_ID_RE.match(run_id)
    if match:
        return f"{match.group(1)}{int(match.group(2)) + 1}"
    return default


def next_campaign_run_id(agent_id: str, latest_run_id: str | None) -> str:
    """Run id for the next campaign + evaluation execution.

    Before the first apply, re-use the latest run (typically ``run_1``).
    After apply, allocate the next sequential id (``run_2``, ``run_3``, …).
    """
    if not latest_run_id:
        return "run_1"
    apply_history = get_apply_history()
    if not any(entry.get("agent_id") == agent_id for entry in apply_history):
        return latest_run_id
    return next_run_id(latest_run_id, default="run_2")


def get_latest_run_id_for_agent(agent_id: str) -> str | None:
    """Return the most recent run_id for *agent_id* from run_index, or None."""
    entry = get_latest_run_entry(agent_id)
    return entry.get("run_id") if entry else None


def get_latest_run_entry(agent_id: str) -> dict | None:
    """Return the most recent run_index row for *agent_id*, or None."""
    agent_runs = sorted(
        [r for r in get_run_index() if r.get("agent_id") == agent_id],
        key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
    )
    return agent_runs[-1] if agent_runs else None


def get_run_index_entry(agent_id: str, run_id: str) -> dict | None:
    """Return the run_index row for a specific (*agent_id*, *run_id*)."""
    for row in get_run_index():
        if row.get("agent_id") == agent_id and row.get("run_id") == run_id:
            return row
    return None


def reflection_id_for_run(agent_id: str, run_id: str) -> str | None:
    """Return the reflection_id recorded on this run, if any."""
    entry = get_run_index_entry(agent_id, run_id)
    if not entry:
        return None
    return entry.get("reflection_id")


def run_id_for_reflection(agent_id: str, reflection_id: str) -> str | None:
    """Return the run_id whose reflection step produced *reflection_id*."""
    for row in reversed(get_run_index()):
        if row.get("agent_id") == agent_id and row.get("reflection_id") == reflection_id:
            return row.get("run_id")
    return None


def is_reflection_applied(agent_id: str, reflection_id: str) -> bool:
    """True when *reflection_id* appears in apply_history for this agent."""
    return any(
        h.get("reflection_id") == reflection_id
        and h.get("agent_id", agent_id) == agent_id
        for h in get_apply_history()
    )


def get_apply_entry(agent_id: str, reflection_id: str) -> dict | None:
    """Return the apply_history row for (*agent_id*, *reflection_id*), if any."""
    for row in reversed(get_apply_history()):
        if row.get("agent_id") == agent_id and row.get("reflection_id") == reflection_id:
            return row
    return None


def list_reflections_for_agent(agent_id: str) -> list[dict]:
    """All reflections for an agent, newest ``refl_N`` first."""
    seen: set[str] = set()
    items: list[dict] = []

    def _add(reflection_id: str, run_id: str | None) -> None:
        if reflection_id in seen:
            return
        seen.add(reflection_id)
        items.append(
            {
                "reflection_id": reflection_id,
                "run_id": run_id or run_id_for_reflection(agent_id, reflection_id),
                "applied": is_reflection_applied(agent_id, reflection_id),
            }
        )

    for row in reversed(get_run_index()):
        if row.get("agent_id") == agent_id and row.get("reflection_id"):
            _add(str(row["reflection_id"]), row.get("run_id"))

    refl_root = _DATA / agent_id / "outputs" / "reflections"
    if refl_root.is_dir():
        for path in refl_root.iterdir():
            if path.is_dir() and _REFL_ID_RE.match(path.name):
                _add(path.name, run_id_for_reflection(agent_id, path.name))

    items.sort(
        key=lambda r: int(_REFL_ID_RE.match(r["reflection_id"]).group(1)),  # type: ignore[union-attr]
        reverse=True,
    )
    return items


def snapshots_before_reflection(agent_id: str, reflection_id: str) -> tuple[list[dict], str]:
    """Prompt + skill as they were on the eval run that triggered this reflection."""
    source_run = run_id_for_reflection(agent_id, reflection_id)
    if source_run:
        entry = get_run_index_entry(agent_id, source_run)
        if entry:
            skill = entry.get("skill_snapshot") or ""
            raw = entry.get("prompt_snapshot") or "[]"
            try:
                prompt = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                prompt = []
            if isinstance(prompt, list):
                return prompt, skill
    return get_system_prompt(agent_id), get_skill_text(agent_id)


def run_has_evaluation(entry: dict | None) -> bool:
    """True when a run_index row (or aggregate file) indicates eval completed."""
    if not entry:
        return False
    return entry.get("pass_rate") is not None or entry.get("mean_score") is not None


def verification_run_after_last_apply(agent_id: str) -> str | None:
    """Run id expected immediately after the most recent apply (before next reflect)."""
    history = [h for h in get_apply_history() if h.get("agent_id") == agent_id]
    if not history:
        return None
    last_refl = history[-1].get("reflection_id")
    if not last_refl:
        return None
    source_run = run_id_for_reflection(agent_id, last_refl)
    if not source_run:
        return None
    return next_run_id(source_run, default="run_2")


def next_reflection_id(agent_id: str) -> str:
    """Next sequential reflection id for this agent (``refl_1``, ``refl_2``, …)."""
    max_seq = 0
    refl_root = _DATA / agent_id / "outputs" / "reflections"
    if refl_root.is_dir():
        for path in refl_root.iterdir():
            match = _REFL_ID_RE.match(path.name)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
    for row in get_run_index():
        if row.get("agent_id") != agent_id:
            continue
        match = _REFL_ID_RE.match(row.get("reflection_id") or "")
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return f"refl_{max_seq + 1}"


def get_eval_cases(agent_id: str) -> list[dict]:
    """Return eval cases list from disk for *agent_id*."""
    data = _read_json(_DATA / agent_id / "evaluation" / "eval_cases.json")
    if isinstance(data, list):
        return data
    return []


def get_latest_score_for_agent(agent_id: str) -> float | None:
    """Return the mean_score from the latest run's run_index entry."""
    run_index = get_run_index()
    agent_runs = [r for r in run_index if r.get("agent_id") == agent_id]
    if not agent_runs:
        return None
    agent_runs.sort(key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)), reverse=True)
    score = agent_runs[0].get("mean_score")
    return float(score) if score is not None else None
