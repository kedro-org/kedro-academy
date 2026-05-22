"""Streamlit dashboard entry point for the B2B campaign agent reflection demo.

Run with:  streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from app.state import (
    DEFAULT_STATE_PATH,
    DemoState,
    load_demo_state,
    reset_demo_state,
    save_demo_state,
    transition,
)
from app import ui_components as ui
from app.components import step_1_run, step_2_reflect, step_3_rerun

_KEDRO_AVATAR = "https://avatars.githubusercontent.com/kedro-org"

_STEP_INDEX = {
    "idle": 0,
    "run_1_done": 1,
    "reflected": 1,
    "applied": 2,
    "run_2_done": 3,
}

STATE_PATH = _PROJECT_ROOT / "data" / "demo_state.json"


def _do_reset() -> None:
    import subprocess
    subprocess.run(
        [sys.executable, str(_PROJECT_ROOT / "scripts" / "seed_demo.py")],
        cwd=str(_PROJECT_ROOT),
        check=False,
    )
    reset_demo_state(STATE_PATH)
    st.cache_data.clear()
    st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="B2B Campaign Agent — Reflection Demo",
        page_icon=_KEDRO_AVATAR,
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={},
    )

    ui.inject_global_css()
    ui.inject_page_chrome(kedro_avatar_url=_KEDRO_AVATAR)

    demo = load_demo_state(STATE_PATH)

    hcol, rcol = st.columns([11, 1])
    with hcol:
        ui.page_header(kedro_avatar_url=_KEDRO_AVATAR)
    with rcol:
        st.markdown(
            '<div style="padding-top:26px;display:flex;justify-content:flex-end;">',
            unsafe_allow_html=True,
        )
        if st.button("Reset", key="reset_top", help="Clears all run data and restores initial state"):
            _do_reset()
        st.markdown("</div>", unsafe_allow_html=True)

    ui.workflow_bar(_STEP_INDEX.get(demo.state, 0))

    step_1_run.render(demo)
    st.divider()
    step_2_reflect.render(demo)
    st.divider()
    step_3_rerun.render(demo)


if __name__ == "__main__":
    main()
