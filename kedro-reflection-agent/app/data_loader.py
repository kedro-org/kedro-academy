"""Data loader functions for the Reflection Hub dashboard.

All functions read from disk. They never throw — missing files return
sensible empty defaults so the UI can render gracefully before any
pipelines have run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
    """Read the global run index (data/outputs/run_index.json)."""
    data = _read_json(_DATA / "outputs" / "run_index.json")
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
    data = _read_json(primary) or _read_json(fallback)
    if isinstance(data, list):
        return data
    # Also look in the global signal_index, filtered by agent+run
    signal_index = _read_json(_DATA / "outputs" / "signal_index.json")
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

def get_reflection_summary(reflection_id: str) -> str:
    """Read reflections/{reflection_id}/summary.md — searches common locations."""
    for base in [
        _DATA / "outputs" / "reflections" / reflection_id / "summary.md",
        _DATA / "b2b_sales" / "outputs" / "reflections" / reflection_id / "summary.md",
        _DATA / "consumer_mktg" / "outputs" / "reflections" / reflection_id / "summary.md",
        _DATA / "customer_care" / "outputs" / "reflections" / reflection_id / "summary.md",
    ]:
        if base.exists():
            try:
                return base.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
    return ""


def get_proposed_prompt(reflection_id: str) -> list[dict]:
    for base in [
        _DATA / "outputs" / "reflections" / reflection_id / "proposed_prompt.json",
        _DATA / "b2b_sales" / "outputs" / "reflections" / reflection_id / "proposed_prompt.json",
    ]:
        data = _read_json(base)
        if isinstance(data, list):
            return data
    return []


def get_proposed_skill(reflection_id: str) -> str:
    for base in [
        _DATA / "outputs" / "reflections" / reflection_id / "proposed_skill.md",
        _DATA / "b2b_sales" / "outputs" / "reflections" / reflection_id / "proposed_skill.md",
    ]:
        if base.exists():
            try:
                return base.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
    return ""


# ── Apply history ─────────────────────────────────────────────────────────────

def get_apply_history() -> list[dict]:
    data = _read_json(_DATA / "outputs" / "apply_history.json")
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

def get_latest_run_id_for_agent(agent_id: str) -> str | None:
    """Return the most recent run_id for *agent_id* from run_index, or None."""
    run_index = get_run_index()
    agent_runs = [r for r in run_index if r.get("agent_id") == agent_id]
    if not agent_runs:
        return None
    # Sort by started_at descending, fall back to run_seq
    agent_runs.sort(key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)), reverse=True)
    return agent_runs[0].get("run_id")


def get_latest_score_for_agent(agent_id: str) -> float | None:
    """Return the mean_score from the latest run's run_index entry."""
    run_index = get_run_index()
    agent_runs = [r for r in run_index if r.get("agent_id") == agent_id]
    if not agent_runs:
        return None
    agent_runs.sort(key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)), reverse=True)
    score = agent_runs[0].get("mean_score")
    return float(score) if score is not None else None
