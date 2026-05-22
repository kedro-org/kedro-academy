"""Demo state machine.

The dashboard walks through:
    idle -> run_1_done -> reflected -> applied -> run_2_done

State is persisted to data/demo_state.json so a browser refresh resumes
correctly. Each step also derives state from artifacts on disk as a fallback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

DemoStateName = Literal["idle", "run_1_done", "reflected", "applied", "run_2_done"]

DEFAULT_STATE_PATH = Path("data/demo_state.json")

_RUN_1_SENTINEL = Path("data/outputs/runs/run_1/aggregate_scores.json")
_REFLECTED_SENTINEL = Path("data/outputs/reflections/refl_1/summary.md")
_APPLIED_SENTINEL = Path("data/outputs/apply_history.json")
_RUN_2_SENTINEL = Path("data/outputs/runs/run_2/aggregate_scores.json")


class DemoState(BaseModel):
    state: DemoStateName = "idle"
    run_1_id: str | None = None
    reflection_id: str | None = None
    applied_id: str | None = None
    run_2_id: str | None = None
    seed_at: str | None = None  # set by seed script; detected by UI to clear cache

    def can_run_agent_step1(self) -> bool:
        return self.state == "idle"

    def can_run_reflection(self) -> bool:
        return self.state == "run_1_done"

    def can_apply(self) -> bool:
        return self.state == "reflected"

    def can_run_agent_step3(self) -> bool:
        return self.state == "applied"


def _derive_state() -> DemoStateName:
    """Infer the current demo state from artifacts present on disk."""
    if _RUN_2_SENTINEL.exists():
        return "run_2_done"
    if _APPLIED_SENTINEL.exists():
        return "applied"
    if _REFLECTED_SENTINEL.exists():
        return "reflected"
    if _RUN_1_SENTINEL.exists():
        return "run_1_done"
    return "idle"


def load_demo_state(path: Path | None = None) -> DemoState:
    """Load state from JSON, falling back to disk-artifact derivation."""
    state_path = path or DEFAULT_STATE_PATH
    if state_path.exists():
        try:
            return DemoState.model_validate(json.loads(state_path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    return DemoState(state=_derive_state())


def save_demo_state(state: DemoState, path: Path | None = None) -> None:
    state_path = path or DEFAULT_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def transition(state: DemoState, new_state: DemoStateName, **kwargs: str | None) -> DemoState:
    data = state.model_dump()
    data["state"] = new_state
    data.update({k: v for k, v in kwargs.items() if v is not None})
    return DemoState.model_validate(data)


def reset_demo_state(path: Path | None = None) -> DemoState:
    fresh = DemoState()
    save_demo_state(fresh, path)
    return fresh
