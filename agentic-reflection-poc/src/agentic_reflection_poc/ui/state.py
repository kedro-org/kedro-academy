"""Demo state machine helpers for Streamlit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

DemoStateName = Literal["idle", "run_1_done", "reflected", "applied", "run_2_done"]

DEFAULT_STATE_PATH = Path("data/demo_state.json")


class DemoState(BaseModel):
    state: DemoStateName = "idle"
    run_1_id: str | None = None
    proposal_id: str | None = None
    applied_id: str | None = None
    run_2_id: str | None = None

    def can_run_agent_step1(self) -> bool:
        return self.state == "idle"

    def can_run_reflection(self) -> bool:
        return self.state == "run_1_done"

    def can_apply(self) -> bool:
        return self.state == "reflected"

    def can_run_agent_step3(self) -> bool:
        return self.state == "applied"


def load_demo_state(path: Path | None = None) -> DemoState:
    state_path = path or DEFAULT_STATE_PATH
    if not state_path.exists():
        return DemoState()
    return DemoState.model_validate(json.loads(state_path.read_text(encoding="utf-8")))


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
    state = DemoState()
    save_demo_state(state, path)
    return state
