"""Org Overview page — minimal stub for Phase 1."""

from __future__ import annotations

import streamlit as st

from app.components.nav import render_nav
from app.data_loader import get_agent_ids, get_latest_score_for_agent, get_run_index
from app.components.agent_selector import AGENTS


def render() -> None:
    """Render the org overview page (stub)."""
    render_nav("overview")

    st.markdown(
        """
        <div style="padding:16px 0 24px 0;">
          <h1 style="font-size:24px;font-weight:800;color:#0F172A;margin:0 0 4px 0;
                     letter-spacing:-0.02em;">Org Overview</h1>
          <p style="font-size:14px;color:#64748B;margin:0;">
            All campaign agents and their latest performance metrics.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    run_index = get_run_index()

    cols = st.columns(3)
    for col, agent_id in zip(cols, get_agent_ids()):
        cfg = AGENTS.get(agent_id, {})
        label = cfg.get("label", agent_id)
        icon = cfg.get("icon", "🤖")
        color = cfg.get("color", "#2251FF")
        score = get_latest_score_for_agent(agent_id)
        score_display = f"{round(score * 100)}%" if score is not None else "—"

        agent_runs = [r for r in run_index if r.get("agent_id") == agent_id]
        n_runs = len(agent_runs)

        with col:
            st.markdown(
                f"""
                <div class="card" style="border-top:3px solid {color};text-align:center;
                                         cursor:pointer;">
                  <div style="font-size:32px;margin-bottom:8px;">{icon}</div>
                  <div style="font-size:16px;font-weight:700;color:#0F172A;margin-bottom:4px;">
                    {label}
                  </div>
                  <div style="font-size:28px;font-weight:800;color:{color};
                               letter-spacing:-0.02em;">
                    {score_display}
                  </div>
                  <div style="font-size:12px;color:#94A3B8;margin-top:4px;">
                    {n_runs} run{'s' if n_runs != 1 else ''}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
