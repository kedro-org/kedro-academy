"""Shared Kedro-Viz tab renderer — reused across all pipeline stages."""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components_v1

_PROJECT_ROOT = Path(__file__).parent.parent.parent


def render_kedro_viz(
    agent_id: str,
    pipelines: list[str],
    *,
    stage_key: str,
) -> None:
    """Render the Kedro-Viz iframe with a pipeline picker.

    Args:
        agent_id:   Current agent (used for session-state keys and params).
        pipelines:  Pipeline names shown in the picker (e.g. ["campaign", "evaluation"]).
        stage_key:  Short unique key for the stage (e.g. "campaign", "scouts", "apply").
                    Used to namespace session-state and widget keys.
    """
    from app.kedro_viz_server import KEDRO_VIZ_BASE, ensure_kedro_viz_running

    # ── Pipeline picker ───────────────────────────────────────────────────────
    left_col, right_col = st.columns([6, 1])
    with left_col:
        sess_key = f"viz_pip_{stage_key}_{agent_id}"
        default_pip = st.session_state.get(sess_key, pipelines[0])
        if default_pip not in pipelines:
            default_pip = pipelines[0]

        if len(pipelines) == 1:
            pipeline = pipelines[0]
        else:
            pipeline = st.segmented_control(
                "Pipeline",
                options=pipelines,
                format_func=lambda x: x.replace("_", " ").title(),
                default=default_pip,
                key=f"viz_pip_ctrl_{stage_key}_{agent_id}",
                label_visibility="collapsed",
            )
            if pipeline:
                st.session_state[sess_key] = pipeline
            else:
                pipeline = default_pip

    with right_col:
        st.markdown(
            f'<div style="text-align:right;padding-top:8px;">'
            f'<a href="{KEDRO_VIZ_BASE}" target="_blank" '
            f'style="font-size:12px;font-weight:600;color:#2251FF;text-decoration:none;">'
            f'Open in new tab ↗</a></div>',
            unsafe_allow_html=True,
        )

    # ── Ensure server is running ──────────────────────────────────────────────
    _agent = st.session_state.get("agent_id", agent_id)
    status = ensure_kedro_viz_running(
        _PROJECT_ROOT, agent_params=f"agent_id={_agent}"
    )

    if status == "ready":
        url = f"{KEDRO_VIZ_BASE}/?pid={pipeline}&expandAllPipelines=true"
        components_v1.iframe(url, height=500, scrolling=True)

    elif status == "starting":
        st.markdown(
            '<div style="background:#0F172A;border-radius:12px;height:500px;'
            'display:flex;flex-direction:column;align-items:center;'
            'justify-content:center;gap:12px;text-align:center;padding:32px;">'
            '<div style="font-size:14px;font-weight:600;color:#E2E8F0;">'
            'Kedro-Viz starting…</div>'
            '<div style="font-size:12px;color:#64748B;">Hang tight, the server is booting.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        time.sleep(1)
        st.rerun()

    elif status == "failed":
        err = st.session_state.get("kedro_viz_error", "unknown error")
        st.error(f"Kedro-Viz failed to start: {err}")

    else:  # unavailable — kedro not on PATH
        st.markdown(
            '<div style="background:#0F172A;border-radius:12px;height:500px;'
            'display:flex;flex-direction:column;align-items:center;'
            'justify-content:center;gap:16px;text-align:center;padding:32px;">'
            '<div style="font-size:15px;font-weight:700;color:#E2E8F0;">'
            'kedro not found on PATH</div>'
            '<div style="font-size:13px;color:#64748B;max-width:300px;line-height:1.5;">'
            'Activate the project virtualenv and restart Streamlit.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
