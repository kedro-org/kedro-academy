"""Multi-run Insights section — matches the HTML mockup layout.

Layout: 2-column grid
  Left (60%): score progression line chart with reflection event markers
  Right (40%): dimension delta table (before→after bars + delta)
Below: "What drove it" apply history box
"""

from __future__ import annotations

import streamlit as st

from app.components.charts import score_progression_chart
from app.components.icons import ic
from app.data_loader import get_apply_history


def render_multi_run_insights(agent_id: str, run_index: list[dict]) -> None:
    """Render the Multi-run Insights card."""
    agent_runs = sorted(
        [r for r in run_index if r.get("agent_id") == agent_id],
        key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
    )

    # ── Section header (card-style) ───────────────────────────────────────────
    trending_icon = ic("trending-up", 14, "#94A3B8")
    bar_icon = ic("bar-chart-2", 14, "#94A3B8")

    # Section heading — outside the st.container so it floats above
    st.markdown(
        f"""
        <div style="display:flex;align-items:flex-start;justify-content:space-between;
                    gap:12px;margin-bottom:8px;">
          <div>
            <div style="font-size:11px;font-weight:700;color:#94A3B8;
                        text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px;">
              Cross-run
            </div>
            <div style="font-size:17px;font-weight:800;color:#0F172A;letter-spacing:-0.02em;">
              Multi-run Insights
            </div>
            <div style="font-size:12px;color:#94A3B8;margin-top:2px;">
              Score progression and dimension improvement across all runs for this agent.
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;font-size:11px;color:#64748B;
                      flex-shrink:0;padding-top:4px;">
            <span style="width:8px;height:8px;border-radius:50%;background:#CBD5E1;
                         display:inline-block;"></span>run_1 baseline
            <span style="width:8px;height:8px;border-radius:50%;background:#2251FF;
                         display:inline-block;margin-left:4px;"></span>latest run
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not agent_runs:
        st.markdown(
            """
            <div style="background:#fff;border:1px solid #E2E8F0;border-radius:16px;
                        padding:40px 24px;text-align:center;color:#94A3B8;">
              <div style="font-size:32px;margin-bottom:10px;">📉</div>
              <div style="font-size:14px;font-weight:600;color:#64748B;">No runs yet</div>
              <div style="font-size:13px;margin-top:4px;">
                Run the campaign pipeline to start tracking progress.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # ── Two-column layout: chart | dimension delta ────────────────────────────
    col_chart, col_delta = st.columns([3, 2], gap="large")

    with col_chart:
        st.markdown(
            f'<div style="font-size:13px;font-weight:600;color:#0F172A;'
            f'margin-bottom:6px;display:flex;align-items:center;gap:6px;">'
            f'{trending_icon} Score progression · with reflection events</div>',
            unsafe_allow_html=True,
        )
        fig = score_progression_chart(run_index, agent_id)
        if fig:
            st.plotly_chart(fig, config={"displayModeBar": False}, width="stretch")
        else:
            st.markdown(
                '<div style="height:160px;background:#F8FAFC;border:1px solid #E2E8F0;'
                'border-radius:10px;display:flex;align-items:center;justify-content:center;'
                'color:#94A3B8;font-size:13px;">Run multiple campaigns to see progression.</div>',
                unsafe_allow_html=True,
            )

    with col_delta:
        st.markdown(
            f'<div style="font-size:13px;font-weight:600;color:#0F172A;'
            f'margin-bottom:10px;display:flex;align-items:center;gap:6px;">'
            f'{bar_icon} Dimension change · run_1 → latest</div>',
            unsafe_allow_html=True,
        )
        _render_dimension_delta(agent_runs)

    # ── "What drove it" box ───────────────────────────────────────────────────
    apply_history = get_apply_history()
    if apply_history:
        latest = apply_history[-1]
        refl_id = latest.get("reflection_id") or "—"
        applied_at = (latest.get("applied_at") or "")[:10]
        new_skill = latest.get("new_skill_text") or ""
        new_prompt = latest.get("new_prompt_messages") or []
        n_cases = len(latest.get("new_eval_case_ids") or [])

        items: list[str] = []
        if new_prompt:
            items.append("System prompt updated with targeted improvements")
        if new_skill:
            items.append("Skill file updated with new writing guidelines")
        if n_cases:
            items.append(f"{n_cases} regression eval cases added to prevent re-introduction of failures")

        items_html = "".join(
            f'<li style="margin-bottom:5px;color:#475569;">{item}</li>' for item in items
        )
        st.markdown(
            f"""
            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
                        padding:14px 18px;margin-top:8px;">
              <span style="font-weight:700;color:#0F172A;font-size:13px;">
                What drove it:
              </span>
              <span style="color:#64748B;font-size:12px;margin-left:6px;">
                Applied from <code style="background:#F1F5F9;padding:1px 5px;border-radius:3px;
                font-size:11px;">{refl_id}</code>{' · ' + applied_at if applied_at else ''}
              </span>
              <ul style="font-size:13px;margin:8px 0 0 0;padding-left:18px;line-height:1.7;">
                {items_html}
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_dimension_delta(agent_runs: list[dict]) -> None:
    """Show before→after dimension bars + delta values."""
    if len(agent_runs) < 2:
        # Single run — just show current scores
        run = agent_runs[-1]
        scores: dict[str, float] = run.get("mean_per_scorer") or {}
        if not scores:
            st.markdown(
                '<div style="color:#94A3B8;font-size:13px;">Run evaluation to see dimension scores.</div>',
                unsafe_allow_html=True,
            )
            return
        for dim, val in list(scores.items())[:6]:
            _bar_row(dim, None, val)
        return

    run1 = agent_runs[0]
    run2 = agent_runs[-1]
    scores1: dict[str, float] = run1.get("mean_per_scorer") or {}
    scores2: dict[str, float] = run2.get("mean_per_scorer") or {}
    all_dims = [d for d in scores2 if d in scores1] or list(scores2.keys())[:6]

    for dim in all_dims[:6]:
        v1 = float(scores1.get(dim, 0))
        v2 = float(scores2.get(dim, 0))
        _bar_row(dim, v1, v2)

    # "What drove it" note under the bars
    mean1 = run1.get("mean_score") or 0
    mean2 = run2.get("mean_score") or 0
    delta = float(mean2) - float(mean1)
    delta_col = "#15803D" if delta >= 0 else "#B91C1C"
    sign = "+" if delta >= 0 else ""
    st.markdown(
        f"""
        <div style="margin-top:14px;padding:10px 14px;background:#F8FAFC;
                    border:1px solid #E2E8F0;border-radius:8px;">
          <span style="font-size:12px;color:#64748B;">Overall: </span>
          <span style="font-size:13px;font-weight:700;color:#0F172A;">{mean1:.2f}</span>
          <span style="color:#94A3B8;margin:0 4px;">→</span>
          <span style="font-size:13px;font-weight:800;color:#0F172A;">{mean2:.2f}</span>
          <span style="font-size:13px;font-weight:700;color:{delta_col};margin-left:6px;">
            {sign}{delta:.2f}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _bar_row(dim: str, v1: float | None, v2: float) -> None:
    """Render one dimension row with overlaid before/after bars and delta.

    Matches the HTML mockup: grey bar for run_1 baseline, blue bar for run_2
    overlaid on top (slightly transparent), delta shown in green.
    """
    pct2 = int(v2 * 100)
    label = dim.replace("_", " ").title()

    if v1 is not None:
        delta = v2 - v1
        sign = "+" if delta >= 0 else ""
        delta_col = "#15803D" if delta >= 0 else "#B91C1C"
        delta_html = (
            f'<span style="font-size:11px;font-weight:700;color:{delta_col};margin-left:4px;">'
            f'{sign}{delta:.2f}</span>'
        )
        v1_pct = int(v1 * 100)
        # run_1 grey bar (behind)
        before_bar = (
            f'<div style="position:absolute;left:0;top:0;bottom:0;width:{v1_pct}%;'
            f'background:#CBD5E1;border-radius:100px;"></div>'
        )
        value_html = (
            f'<span style="color:#94A3B8;">{v1:.2f} → '
            f'<strong style="color:#15803D">{v2:.2f}</strong></span>'
            f'{delta_html}'
        )
    else:
        before_bar = ""
        delta_html = ""
        value_html = f'<span style="font-weight:700;color:#0F172A;">{v2:.2f}</span>'

    st.markdown(
        f"""
        <div style="margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;
                      font-size:11px;margin-bottom:4px;">
            <span style="color:#475569;">{label}</span>
            <span>{value_html}</span>
          </div>
          <div style="position:relative;height:6px;background:#F1F5F9;border-radius:100px;overflow:hidden;">
            {before_bar}
            <div style="position:absolute;left:0;top:0;bottom:0;width:{pct2}%;
                        background:#2251FF;opacity:0.75;border-radius:100px;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
