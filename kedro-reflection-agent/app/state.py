"""Demo state machine.

The dashboard walks through:
    idle -> run_1_done -> reflected -> applied -> run_2_done

State is derived from artifacts on disk so a browser refresh resumes correctly.
Buttons in each step are gated by the current state so the demo can only be
clicked through in order.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

# Ordered list of states — index used for "has this step been reached" checks.
STATES: list[str] = ["idle", "run_1_done", "reflected", "applied", "run_2_done"]

_RUN_1_SENTINEL = Path("data/outputs/runs/run_1/aggregate_scores.json")
_REFLECTED_SENTINEL = Path("data/outputs/reflections/refl_1/summary.md")
_APPLIED_SENTINEL = Path("data/outputs/apply_history.json")
_RUN_2_SENTINEL = Path("data/outputs/runs/run_2/aggregate_scores.json")


def derive_state() -> str:
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


def get_state() -> str:
    """Return the current state, initialising from disk on first call."""
    if "demo_state" not in st.session_state:
        st.session_state.demo_state = derive_state()
    return st.session_state.demo_state


def set_state(state: str) -> None:
    st.session_state.demo_state = state


def state_index() -> int:
    return STATES.index(get_state())


def reached(state: str) -> bool:
    """Return True if the demo has reached or passed the given state."""
    return state_index() >= STATES.index(state)
