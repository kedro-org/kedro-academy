"""Campaign page — the main view of the Reflection Hub."""

from __future__ import annotations

import streamlit as st

from app.components.agent_selector import render_agent_selector
from app.components.header_card import render_header_card
from app.components.multi_run import render_multi_run_insights
from app.components.nav import render_nav
from app.components.stage_approve import render_stage_approve
from app.components.stage_campaign import render_stage_campaign
from app.components.stage_reflect import render_stage_reflect
from app.components.stage_scouts import render_stage_scouts
from app.data_loader import get_apply_history, get_run_index
from app.state import load_demo_state


def _resolve_run_ids(agent_id: str, run_index: list[dict]) -> tuple[str | None, str | None]:
    """Return (latest_run_id, reflection_id) for the current agent."""
    agent_runs = sorted(
        [r for r in run_index if r.get("agent_id") == agent_id],
        key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
    )
    run_id: str | None = agent_runs[-1].get("run_id") if agent_runs else None

    reflection_id: str | None = None
    for r in reversed(agent_runs):
        if r.get("reflection_id"):
            reflection_id = r["reflection_id"]
            break
    if not reflection_id:
        history = get_apply_history()
        if history:
            reflection_id = history[-1].get("reflection_id")

    return run_id, reflection_id


def render() -> None:
    """Render the full campaign page."""
    from pathlib import Path

    render_nav("campaigns")

    # ── Agent selector ────────────────────────────────────────────────────────
    current_agent = st.session_state.get("agent_id", "b2b_sales")
    new_agent = render_agent_selector(current_agent)
    if new_agent != current_agent:
        st.session_state["agent_id"] = new_agent
        st.rerun()
    agent_id = new_agent

    # ── Data ──────────────────────────────────────────────────────────────────
    run_index = get_run_index()
    run_id, reflection_id = _resolve_run_ids(agent_id, run_index)

    state_path = Path(__file__).parent.parent.parent / "data" / "demo_state.json"
    demo_state = load_demo_state(state_path)

    # ── Header card ───────────────────────────────────────────────────────────
    render_header_card(agent_id, run_index)

    # ── Pipeline Observability — ONE card wrapping header + all stage tabs ───────
    with st.container(border=True):
        run_id_badge = ""
        if run_id:
            run_id_badge = (
                f'<span style="background:#EEF2FF;color:#2251FF;font-size:12px;font-weight:600;'
                f'padding:4px 12px;border-radius:100px;border:1px solid #C7D2FE;">'
                f'{run_id} · active</span>'
            )
        # Card header: Observability label + title + run badge
        st.markdown(
            f"""
            <div style="display:flex;align-items:flex-start;justify-content:space-between;
                        gap:12px;padding-bottom:12px;">
              <div>
                <div style="font-size:11px;font-weight:700;color:#94A3B8;
                            text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px;">
                  Observability
                </div>
                <div style="font-size:17px;font-weight:800;color:#0F172A;
                            letter-spacing:-0.02em;">Pipeline Runs</div>
                <div style="font-size:12px;color:#94A3B8;margin-top:2px;">
                  Kedro-Viz · live logs · Langfuse — one tab per pipeline stage.
                </div>
              </div>
              <div style="flex-shrink:0;">{run_id_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── 4 Stage tabs (inside the card) ───────────────────────────────────
        t1, t2, t3, t4 = st.tabs([
            "Campaign & Evaluate",
            "Scouts",
            "Reflect & Propose",
            "Approve & Apply",
        ])

        with t1:
            render_stage_campaign(agent_id, run_id, demo_state)
        with t2:
            render_stage_scouts(agent_id, run_id)
        with t3:
            render_stage_reflect(agent_id, run_id, reflection_id, demo_state)
        with t4:
            render_stage_approve(agent_id, run_id, reflection_id, demo_state)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Multi-run insights (wrapped in a native bordered container = card) ──────
    with st.container(border=True):
        render_multi_run_insights(agent_id, run_index)
