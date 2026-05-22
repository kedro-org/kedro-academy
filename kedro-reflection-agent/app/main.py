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

from app import state as demo_state
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

    current_state = demo_state.get_state()

    hcol, rcol = st.columns([11, 1])
    with hcol:
        ui.page_header(kedro_avatar_url=_KEDRO_AVATAR)
    with rcol:
        st.markdown(
            '<div style="padding-top:26px;display:flex;justify-content:flex-end;">',
            unsafe_allow_html=True,
        )
        if st.button("Reset", key="reset_top", help="Clears demo state derived from disk"):
            demo_state.set_state("idle")
            st.cache_data.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    ui.workflow_bar(_STEP_INDEX.get(current_state, 0))

    step_1_run.render(current_state)
    st.divider()
    step_2_reflect.render(current_state)
    st.divider()
    step_3_rerun.render(current_state)


if __name__ == "__main__":
    main()
