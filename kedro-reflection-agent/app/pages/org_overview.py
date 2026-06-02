"""Org Overview page — all agents at a glance."""

from __future__ import annotations

import streamlit as st

from app.components.nav import render_nav
from app.components.agent_selector import AGENTS
from app.components.charts import portfolio_trend_chart, dimension_radar_chart
from app.data_loader import (
    get_agent_ids,
    get_apply_history,
    get_eval_cases,
    get_latest_score_for_agent,
    get_run_index,
)


# ── Agent meta helpers ────────────────────────────────────────────────────────

_AGENT_ICONS = {
    "b2b_sales": (
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="2" y="7" width="20" height="14" rx="2"/>'
        '<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>'
    ),
    "consumer_mktg": (
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>'
        '<line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></svg>'
    ),
    "customer_care": (
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/>'
        '<path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3z"/>'
        '<path d="M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/></svg>'
    ),
}

_AGENT_LABEL_SHORT = {
    "b2b_sales": "B2B Sales",
    "consumer_mktg": "Cons. Marketing",
    "customer_care": "Customer Care",
}

_AGENT_LABEL_FULL = {
    "b2b_sales": "B2B Sales",
    "consumer_mktg": "Consumer Marketing",
    "customer_care": "Customer Care",
}


def _icon_badge(agent_id: str, size: int = 24) -> str:
    cfg = AGENTS[agent_id]
    svg = _AGENT_ICONS[agent_id].replace('stroke="currentColor"', f'stroke="{cfg["color"]}"')
    return (
        f'<span style="width:{size}px;height:{size}px;border-radius:{size//4}px;'
        f'background:{cfg["bg"]};display:inline-flex;align-items:center;'
        f'justify-content:center;flex-shrink:0;">{svg}</span>'
    )


def _score_chip(score: float) -> str:
    if score >= 0.85:
        return f'<span style="background:#DCFCE7;color:#15803D;font-size:11px;font-weight:700;padding:2px 8px;border-radius:100px;">{score:.2f}</span>'
    if score >= 0.70:
        return f'<span style="background:#FEF9C3;color:#92400E;font-size:11px;font-weight:700;padding:2px 8px;border-radius:100px;">{score:.2f}</span>'
    return f'<span style="background:#FEE2E2;color:#B91C1C;font-size:11px;font-weight:700;padding:2px 8px;border-radius:100px;">{score:.2f}</span>'


def _dim_color(v: float) -> str:
    if v >= 0.80:
        return "#15803D"
    if v >= 0.70:
        return "#92400E"
    return "#B91C1C"


def _dim_bg(v: float) -> str:
    if v >= 0.80:
        return "#DCFCE7"
    if v >= 0.70:
        return "#FEF9C3"
    return "#FEE2E2"


# ── Section 0: Hero ───────────────────────────────────────────────────────────

def _render_hero(active_agents: list[str]) -> None:
    agents_strip = ""
    agent_defs = [
        ("b2b_sales", "#818CF8", "B2B Sales"),
        ("consumer_mktg", "#A78BFA", "Consumer Marketing"),
        ("customer_care", "#2DD4BF", "Customer Care"),
    ]
    for aid, icon_color, label in agent_defs:
        icon_svg = _AGENT_ICONS[aid].replace('stroke="currentColor"', f'stroke="{icon_color}"')
        agents_strip += (
            f'<div style="display:flex;align-items:center;gap:6px;font-size:12px;'
            f'color:#E2E8F0;font-weight:500;">{icon_svg} {label}</div>'
        )

    st.markdown(
        f"""
        <div style="border-radius:16px;overflow:hidden;
                    background:linear-gradient(135deg,#051C2C 0%,#0D2D4A 55%,#0E3460 100%);
                    margin-bottom:20px;">
          <div style="padding:28px 32px 24px 32px;display:flex;gap:32px;align-items:flex-start;">
            <!-- Left: title + description -->
            <div style="flex:1;min-width:0;">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="background:#2251FF;color:#fff;font-size:10px;font-weight:700;
                             padding:3px 10px;border-radius:100px;letter-spacing:0.05em;">
                  Platform Intelligence
                </span>
                <span style="background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.7);
                             font-size:10px;font-weight:600;padding:3px 10px;border-radius:100px;">
                  Kedro · Langfuse · LLM-Judge
                </span>
              </div>
              <h1 style="font-size:22px;font-weight:900;color:#fff;margin:0 0 8px 0;
                         letter-spacing:-0.03em;line-height:1.2;">Org Overview</h1>
              <div style="font-size:13px;color:#CBD5E1;line-height:1.7;margin:0 0 16px 0;
                          max-width:560px;">
                A single view across every AI agent the platform runs. Each agent generates
                outputs, evaluates them automatically, then reflects — proposing targeted
                improvements to its own prompt, skill files, and eval cases. This page tracks
                how those agents are performing <strong style="color:#fff;">right now</strong>,
                how they've improved over time, and what the platform has learned
                <strong style="color:#fff;">across all of them at once</strong>.
              </div>
              <div style="display:flex;flex-wrap:wrap;gap:16px;">
                <div style="display:flex;align-items:center;gap:8px;font-size:11px;color:#94A3B8;">
                  <span style="width:20px;height:20px;border-radius:5px;background:rgba(255,255,255,0.1);
                               display:inline-flex;align-items:center;justify-content:center;">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white"
                         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="23 4 13.5 14 8.5 9 1 16"/>
                      <polyline points="17 4 23 4 23 10"/>
                    </svg>
                  </span>
                  <span><strong style="color:#fff;">Automated reflection loop</strong> — agent improves itself, no manual tuning</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;font-size:11px;color:#94A3B8;">
                  <span style="width:20px;height:20px;border-radius:5px;background:rgba(255,255,255,0.1);
                               display:inline-flex;align-items:center;justify-content:center;">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white"
                         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                  </span>
                  <span><strong style="color:#fff;">Human approval gate</strong> — every change reviewed before it goes live</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;font-size:11px;color:#94A3B8;">
                  <span style="width:20px;height:20px;border-radius:5px;background:rgba(255,255,255,0.1);
                               display:inline-flex;align-items:center;justify-content:center;">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white"
                         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>
                      <circle cx="18" cy="19" r="3"/>
                      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
                      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                    </svg>
                  </span>
                  <span><strong style="color:#fff;">Cross-agent learning</strong> — a fix in one unit surfaces in another</span>
                </div>
              </div>
            </div>
            <!-- Right: pipeline loop steps -->
            <div style="flex-shrink:0;display:flex;flex-direction:column;gap:4px;
                        font-size:11px;font-weight:600;select:none;min-width:120px;">
              {"".join(
                f'<div style="display:flex;align-items:center;gap:6px;">'
                f'<div style="width:108px;padding:5px 0;border-radius:8px;text-align:center;'
                f'background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.8);">{step}</div>'
                f'{"<svg width=12 height=12 viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'rgba(255,255,255,0.3)\' stroke-width=\'2.5\' stroke-linecap=\'round\' stroke-linejoin=\'round\'><line x1=\'12\' y1=\'5\' x2=\'12\' y2=\'19\'/><polyline points=\'19 12 12 19 5 12\'/></svg>" if i < 6 else ""}'
                f'</div>'
                for i, step in enumerate(["Generate", "Evaluate", "Scout", "Reflect", "Propose", "✋ Approve", "Apply"])
              )}
            </div>
          </div>
          <!-- Bottom strip: agents in scope -->
          <div style="border-top:1px solid rgba(255,255,255,0.1);padding:10px 32px;
                      display:flex;flex-wrap:wrap;align-items:center;gap:20px;">
            <span style="font-size:10px;font-weight:700;color:#64748B;
                         text-transform:uppercase;letter-spacing:0.1em;">Agents in scope</span>
            {agents_strip}
            <div style="flex:1;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Section 1: KPI tiles ──────────────────────────────────────────────────────

def _render_kpis(
    portfolio_avg: float | None,
    active_agents: int,
    n_reflections: int,
    n_eval_cases: int,
    avg_lift: float | None,
) -> None:
    cols = st.columns(4, gap="small")

    with cols[0]:
        avg_str = f"{portfolio_avg:.2f}" if portfolio_avg is not None else "—"
        lift_str = f"↑ +{avg_lift:.3f} avg per reflection" if avg_lift else ""
        st.markdown(
            f"""
            <div style="background:#fff;border:1px solid #E2E8F0;border-radius:16px;
                        padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.06);">
              <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                          letter-spacing:.08em;margin-bottom:6px;">Portfolio Avg Score</div>
              <div style="font-size:30px;font-weight:900;color:#0F172A;
                          letter-spacing:-0.03em;line-height:1;">{avg_str}</div>
              {"<div style='font-size:11px;font-weight:600;color:#15803D;margin-top:6px;'>" + lift_str + "</div>" if lift_str else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[1]:
        st.markdown(
            f"""
            <div style="background:#fff;border:1px solid #E2E8F0;border-radius:16px;
                        padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.06);">
              <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                          letter-spacing:.08em;margin-bottom:6px;">Active Agents</div>
              <div style="font-size:30px;font-weight:900;color:#0F172A;
                          letter-spacing:-0.03em;line-height:1;">{active_agents}</div>
              <div style="font-size:11px;color:#94A3B8;margin-top:6px;">of 3 configured</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[2]:
        st.markdown(
            f"""
            <div style="background:#fff;border:1px solid #E2E8F0;border-radius:16px;
                        padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.06);">
              <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                          letter-spacing:.08em;margin-bottom:6px;">Reflections Run</div>
              <div style="font-size:30px;font-weight:900;color:#0F172A;
                          letter-spacing:-0.03em;line-height:1;">{n_reflections}</div>
              <div style="font-size:11px;color:#94A3B8;margin-top:6px;">{n_reflections} applied</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[3]:
        st.markdown(
            f"""
            <div style="background:#fff;border:1px solid #E2E8F0;border-radius:16px;
                        padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,.06);">
              <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                          letter-spacing:.08em;margin-bottom:6px;">Eval Cases</div>
              <div style="font-size:30px;font-weight:900;color:#0F172A;
                          letter-spacing:-0.03em;line-height:1;">{n_eval_cases}</div>
              <div style="font-size:11px;color:#94A3B8;margin-top:6px;">across all agents</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Section 2: Leaderboard ────────────────────────────────────────────────────

def _render_leaderboard(run_index: list[dict]) -> None:
    # Rank agents by latest score
    ranked: list[tuple[str, float, dict]] = []
    for aid in get_agent_ids():
        agent_runs = sorted(
            [r for r in run_index if r.get("agent_id") == aid],
            key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
        )
        if agent_runs:
            latest = agent_runs[-1]
            score = float(latest.get("mean_score") or 0)
            ranked.append((aid, score, latest))
    ranked.sort(key=lambda x: x[1], reverse=True)

    with st.container(border=True):
        # Header
        st.markdown(
            """
            <div style="display:flex;align-items:flex-start;justify-content:space-between;
                        margin-bottom:20px;">
              <div>
                <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                            letter-spacing:.08em;margin-bottom:4px;">Leaderboard</div>
                <div style="font-size:17px;font-weight:800;color:#0F172A;
                            letter-spacing:-0.02em;">Agent Quality Ranking</div>
                <div style="font-size:11px;color:#94A3B8;margin-top:3px;">
                  Score = mean across all evaluation dimensions for the latest run.
                  Each agent improves through its own Generate → Evaluate → Reflect → Apply loop.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not ranked:
            st.info("Run the campaign pipeline for at least one agent to see the leaderboard.")
            return

        # Podium
        _render_podium(ranked)

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # Dimension table
        _render_leaderboard_table(ranked, run_index)

        # Footnote
        st.markdown(
            """
            <div style="margin-top:12px;font-size:11px;color:#94A3B8;background:#F8FAFC;
                        border:1px solid #E2E8F0;border-radius:10px;padding:10px 14px;">
              <strong style="color:#64748B;">How scores are computed:</strong>
              Each agent runs a Langfuse experiment against its eval dataset. An LLM judge
              scores every output on domain dimensions; 4 deterministic heuristics run in
              parallel. The mean across all scorers is the overall score. Dimensions differ
              per agent — Customer Care uses empathy and resolution clarity instead of
              personalisation.
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_podium(ranked: list[tuple[str, float, dict]]) -> None:
    medals = ["🏆", "🥈", "🥉"]
    ranks = ["#1", "#2", "#3"]
    order = [1, 0, 2] if len(ranked) >= 3 else list(range(len(ranked)))

    cols = st.columns([1, 1, 1], gap="medium")
    col_map = {0: cols[1], 1: cols[0], 2: cols[2]}  # center=1st, left=2nd, right=3rd

    for display_pos, source_idx in enumerate(order):
        if source_idx >= len(ranked):
            continue
        aid, score, latest = ranked[source_idx]
        cfg = AGENTS[aid]
        is_first = source_idx == 0
        badge = _icon_badge(aid, 36 if is_first else 32)
        medal = medals[source_idx]
        rank = ranks[source_idx]

        # Compute lift vs first run
        run_seq = latest.get("run_seq", 1)
        delta_str = ""
        if latest.get("delta_mean_score") is not None and run_seq > 1:
            delta = float(latest["delta_mean_score"])
            sign = "+" if delta >= 0 else ""
            delta_col = "#15803D" if delta >= 0 else "#B91C1C"
            delta_str = f'<div style="font-size:10px;font-weight:700;color:{delta_col};margin-top:2px;">{sign}{delta:.2f} vs prev run</div>'

        if is_first:
            card_style = (
                "border-radius:16px;padding:20px 16px;"
                "background:linear-gradient(135deg,#EEF2FF,#E0E7FF);"
                "border:2px solid #2251FF;min-height:130px;"
                "display:flex;flex-direction:column;justify-content:flex-end;align-items:center;"
            )
            rank_style = "font-size:13px;font-weight:800;color:#F59E0B;margin-bottom:6px;text-align:center;"
            name_style = f"font-size:12px;font-weight:700;color:{cfg['color']};margin-top:6px;"
            score_style = "font-size:28px;font-weight:900;color:#0F172A;letter-spacing:-0.02em;line-height:1;"
        else:
            card_style = (
                "border-radius:16px;padding:16px 12px;"
                "background:#F8FAFC;border:1px solid #E2E8F0;min-height:100px;"
                "display:flex;flex-direction:column;justify-content:flex-end;align-items:center;"
            )
            rank_style = "font-size:11px;font-weight:600;color:#94A3B8;margin-bottom:4px;text-align:center;"
            name_style = f"font-size:11px;font-weight:600;color:#64748B;margin-top:4px;"
            score_style = "font-size:22px;font-weight:900;color:#1E293B;letter-spacing:-0.02em;line-height:1;"

        with col_map[display_pos]:
            st.markdown(
                f"""
                <div style="text-align:center;">
                  <div style="{rank_style}">{medal} {rank}</div>
                  <div style="{card_style}">
                    {badge}
                    <div style="{name_style}">{_AGENT_LABEL_SHORT[aid]}</div>
                    <div style="{score_style}">{score:.2f}</div>
                    {delta_str}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_leaderboard_table(
    ranked: list[tuple[str, float, dict]], run_index: list[dict]
) -> None:
    # Build dimension columns: union of all dims across agents, up to 5
    all_dims: dict[str, None] = {}
    for aid, _, latest in ranked:
        mps = latest.get("mean_per_scorer") or {}
        for d in list(mps.keys())[:6]:
            all_dims[d] = None
    dim_cols = list(all_dims.keys())[:5]

    dim_headers = "".join(
        f'<th style="padding:8px 10px;font-size:10px;font-weight:700;color:#94A3B8;'
        f'text-transform:uppercase;letter-spacing:.06em;text-align:center;">'
        f'{d.replace("_"," ").title()}</th>'
        for d in dim_cols
    )

    rows_html = ""
    for rank_idx, (aid, score, latest) in enumerate(ranked):
        cfg = AGENTS[aid]
        icon_svg = _AGENT_ICONS[aid].replace('stroke="currentColor"', f'stroke="{cfg["color"]}"')
        mps = latest.get("mean_per_scorer") or {}
        n_runs = sum(1 for r in run_index if r.get("agent_id") == aid)
        status_pill = (
            '<span style="background:#DCFCE7;color:#15803D;font-size:10px;font-weight:600;'
            'padding:1px 6px;border-radius:100px;border:1px solid #A7F3D0;">Live</span>'
            if n_runs >= 2 else
            '<span style="background:#FEF9C3;color:#92400E;font-size:10px;font-weight:600;'
            'padding:1px 6px;border-radius:100px;border:1px solid #FDE68A;">Running</span>'
            if n_runs == 1 else
            '<span style="background:#F1F5F9;color:#64748B;font-size:10px;font-weight:600;'
            'padding:1px 6px;border-radius:100px;border:1px solid #E2E8F0;">Pending</span>'
        )
        dim_cells = ""
        for d in dim_cols:
            v = mps.get(d)
            if v is not None:
                v = float(v)
                color = _dim_color(v)
                dim_cells += (
                    f'<td style="padding:10px 10px;text-align:center;">'
                    f'<span style="font-size:12px;font-weight:600;color:{color};">{v:.2f}</span></td>'
                )
            else:
                dim_cells += '<td style="padding:10px 10px;text-align:center;color:#CBD5E1;font-size:12px;">—</td>'

        delta_val = latest.get("delta_mean_score")
        delta_html = ""
        if delta_val is not None:
            delta_col = "#15803D" if float(delta_val) >= 0 else "#B91C1C"
            sign = "+" if float(delta_val) >= 0 else ""
            delta_html = f'<span style="font-size:12px;font-weight:700;color:{delta_col};">{sign}{float(delta_val):.2f}</span>'
        else:
            delta_html = '<span style="color:#CBD5E1;font-size:12px;">—</span>'

        rows_html += f"""
        <tr style="border-bottom:1px solid #F8FAFC;">
          <td style="padding:10px 14px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:24px;height:24px;border-radius:6px;background:{cfg['bg']};
                          display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                {icon_svg.replace('width="14"', 'width="12"').replace('height="14"', 'height="12"')}
              </div>
              <span style="font-size:13px;font-weight:600;color:{cfg['color']};">
                {_AGENT_LABEL_SHORT[aid]}
              </span>
              {status_pill}
            </div>
          </td>
          <td style="padding:10px 10px;text-align:center;">
            <span style="font-size:14px;font-weight:900;color:#0F172A;">{score:.2f}</span>
          </td>
          {dim_cells}
          <td style="padding:10px 10px;text-align:center;">{delta_html}</td>
          <td style="padding:10px 14px;text-align:right;">
            <span style="font-size:12px;color:#94A3B8;">{n_runs}</span>
          </td>
        </tr>
        """

    st.markdown(
        f"""
        <div style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;">
            <thead>
              <tr style="border-bottom:1px solid #E2E8F0;">
                <th style="padding:8px 14px;font-size:10px;font-weight:700;color:#94A3B8;
                           text-transform:uppercase;letter-spacing:.06em;text-align:left;">Agent</th>
                <th style="padding:8px 10px;font-size:10px;font-weight:700;color:#94A3B8;
                           text-transform:uppercase;letter-spacing:.06em;text-align:center;">Overall</th>
                {dim_headers}
                <th style="padding:8px 10px;font-size:10px;font-weight:700;color:#94A3B8;
                           text-transform:uppercase;letter-spacing:.06em;text-align:center;">Δ vs Prev</th>
                <th style="padding:8px 14px;font-size:10px;font-weight:700;color:#94A3B8;
                           text-transform:uppercase;letter-spacing:.06em;text-align:right;">Runs</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Section 3: Charts ─────────────────────────────────────────────────────────

def _render_charts(run_index: list[dict]) -> None:
    col_trend, col_radar = st.columns(2, gap="medium")

    # Trend chart
    with col_trend:
        with st.container(border=True):
            st.markdown(
                """
                <div style="margin-bottom:10px;">
                  <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                              letter-spacing:.08em;margin-bottom:3px;">Score Trend Over Time</div>
                  <div style="font-size:14px;font-weight:700;color:#0F172A;">All Agents — Per Run</div>
                  <div style="font-size:11px;color:#94A3B8;margin-top:2px;">
                    Each point = one completed campaign run. Gaps = reflection applied between runs.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            fig = portfolio_trend_chart(run_index)
            if fig:
                st.plotly_chart(fig, config={"displayModeBar": False}, use_container_width=True)
            else:
                st.markdown(
                    '<div style="height:140px;background:#F8FAFC;border:1px solid #E2E8F0;'
                    'border-radius:10px;display:flex;align-items:center;justify-content:center;'
                    'color:#94A3B8;font-size:13px;">Run campaigns to see trends.</div>',
                    unsafe_allow_html=True,
                )

    # Radar chart
    with col_radar:
        with st.container(border=True):
            st.markdown(
                """
                <div style="margin-bottom:10px;">
                  <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                              letter-spacing:.08em;margin-bottom:3px;">Dimension Radar</div>
                  <div style="font-size:14px;font-weight:700;color:#0F172A;">Strength vs. Gap — Latest Run</div>
                  <div style="font-size:11px;color:#94A3B8;margin-top:2px;">
                    Gaps pointing inward = areas targeted by the next reflection.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Build per-agent dimension scores from latest run
            agent_dim_scores: dict[str, dict[str, float]] = {}
            for aid in get_agent_ids():
                agent_runs = sorted(
                    [r for r in run_index if r.get("agent_id") == aid],
                    key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
                )
                if agent_runs:
                    mps = agent_runs[-1].get("mean_per_scorer") or {}
                    if mps:
                        agent_dim_scores[aid] = {k: float(v) for k, v in mps.items()}

            fig = dimension_radar_chart(agent_dim_scores)
            if fig:
                st.plotly_chart(fig, config={"displayModeBar": False}, use_container_width=True)
            else:
                st.markdown(
                    '<div style="height:140px;background:#F8FAFC;border:1px solid #E2E8F0;'
                    'border-radius:10px;display:flex;align-items:center;justify-content:center;'
                    'color:#94A3B8;font-size:13px;">Run evaluation pipelines to see the radar.</div>',
                    unsafe_allow_html=True,
                )


# ── Section 4: Platform Insights ─────────────────────────────────────────────

def _render_insights(run_index: list[dict], apply_history: list[dict]) -> None:
    # Compute insights from real data
    agent_latest: dict[str, dict] = {}
    for aid in get_agent_ids():
        agent_runs = sorted(
            [r for r in run_index if r.get("agent_id") == aid],
            key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
        )
        if agent_runs:
            agent_latest[aid] = agent_runs[-1]

    # Portfolio avg and total runs
    scores = [float(r.get("mean_score") or 0) for r in agent_latest.values()]
    total_runs = len(run_index)
    n_reflections = len(apply_history)

    avg_lift = None
    if n_reflections > 0 and len(scores) >= 1:
        # Estimate avg lift: sum of all positive delta_mean_score across agents
        total_lift = sum(
            float(r.get("delta_mean_score") or 0)
            for r in agent_latest.values()
            if r.get("delta_mean_score") is not None and float(r.get("delta_mean_score") or 0) > 0
        )
        avg_lift = total_lift / max(n_reflections, 1)

    portfolio_avg = sum(scores) / len(scores) if scores else None

    # Find shared weak dims (< 0.75 in 2+ agents)
    dim_weak_agents: dict[str, list[str]] = {}
    for aid, latest in agent_latest.items():
        mps = latest.get("mean_per_scorer") or {}
        for d, v in mps.items():
            if float(v) < 0.75:
                dim_weak_agents.setdefault(d, []).append(aid)
    systemic_dims = [(d, agents) for d, agents in dim_weak_agents.items() if len(agents) >= 2]
    systemic_dims.sort(key=lambda x: -len(x[1]))

    # Find best improvement
    best_improvement: tuple[str, str, float] | None = None
    for aid, latest in agent_latest.items():
        delta = latest.get("delta_mean_score")
        if delta is not None and float(delta) > 0:
            if best_improvement is None or float(delta) > best_improvement[2]:
                best_improvement = (aid, latest.get("run_id", ""), float(delta))

    # Find shared strong dims (>= 0.85 in 2+ agents)
    dim_strong_agents: dict[str, list[str]] = {}
    for aid, latest in agent_latest.items():
        mps = latest.get("mean_per_scorer") or {}
        for d, v in mps.items():
            if float(v) >= 0.85:
                dim_strong_agents.setdefault(d, []).append(aid)
    shared_strengths = [(d, agents) for d, agents in dim_strong_agents.items() if len(agents) >= 2]

    # Summary banner
    avg_str = f"{portfolio_avg:.2f}" if portfolio_avg else "—"
    lift_str = f"+{avg_lift:.3f} per reflection" if avg_lift else "running"
    summary_body = (
        f"Across <strong>{total_runs} campaign run{'s' if total_runs != 1 else ''}</strong> "
        f"and <strong>{n_reflections} reflection{'s' if n_reflections != 1 else ''}</strong>, "
        f"portfolio average sits at <strong>{avg_str}</strong>. "
    )
    if best_improvement:
        bid, brun, bdelta = best_improvement
        summary_body += (
            f"{_AGENT_LABEL_FULL[bid]} leads with the highest run-over-run improvement "
            f"(<strong>+{bdelta:.2f}</strong> in {brun}). "
        )
    if systemic_dims:
        top_dim = systemic_dims[0][0].replace("_", " ")
        summary_body += (
            f"A systemic <strong>\"{top_dim}\"</strong> weakness is active across "
            f"{len(systemic_dims[0][1])} agents — a shared fix could lift the entire portfolio. "
        )

    st.markdown(
        """
        <div style="margin-top:4px;">
          <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                      letter-spacing:.08em;margin-bottom:3px;">Platform Insights</div>
          <div style="font-size:17px;font-weight:800;color:#0F172A;letter-spacing:-0.02em;
                      margin-bottom:3px;">What the system learned across all agents</div>
          <div style="font-size:11px;color:#94A3B8;margin-bottom:14px;">
            Insights aggregated after each reflection cycle from eval scores, failure patterns,
            and applied changes across all agents. Surfaces patterns no single agent can see.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Summary gradient banner
    st.markdown(
        f"""
        <div style="border-radius:16px;padding:20px 24px;margin-bottom:16px;display:flex;gap:16px;
                    background:linear-gradient(135deg,#EEF2FF 0%,#F0FDFA 100%);
                    border:1px solid #C7D2FE;">
          <div style="width:40px;height:40px;border-radius:10px;background:#2251FF;flex-shrink:0;
                      display:flex;align-items:center;justify-content:center;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white"
                 stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
          </div>
          <div>
            <div style="font-size:13px;font-weight:700;color:#0F172A;margin-bottom:4px;">
              Intelligence Summary
            </div>
            <p style="font-size:12px;color:#475569;line-height:1.7;margin:0;">
              {summary_body}
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Insight cards grid — 3 columns
    cards: list[tuple[str, str, str, str, str, str]] = []  # (bg, border, icon_color, title, body, footer)

    # Card 1: Systemic weakness (if any)
    if systemic_dims:
        top_d, top_agents = systemic_dims[0]
        agent_pills = " ".join(
            f'<span style="background:{AGENTS[a]["bg"]};color:{AGENTS[a]["color"]};'
            f'font-size:10px;font-weight:600;padding:2px 8px;border-radius:100px;">'
            f'{_AGENT_LABEL_SHORT[a]}</span>'
            for a in top_agents
        )
        cards.append((
            "#FFFBEB", "#FDE68A", "#D97706",
            f"Systemic: {top_d.replace('_', ' ').title()} Weakness",
            f"{len(top_agents)} agents score below 0.75 on <strong>{top_d.replace('_', ' ')}</strong>. "
            f"A shared prompt or skill fix could lift all affected agents without individual reflection cycles.",
            agent_pills,
        ))
    else:
        cards.append((
            "#F0FDF4", "#BBF7D0", "#15803D",
            "No Systemic Weaknesses",
            "All shared dimensions score above 0.75 across agents. "
            "No cross-agent failure pattern is active right now.",
            '<span style="font-size:11px;font-weight:600;color:#15803D;">✓ All clear</span>',
        ))

    # Card 2: Best improvement / transfer opportunity
    if best_improvement:
        bid, brun, bdelta = best_improvement
        cfg = AGENTS[bid]
        cards.append((
            "#EFF6FF", "#BFDBFE", "#2563EB",
            f"Best Lift: {_AGENT_LABEL_SHORT[bid]} +{bdelta:.2f}",
            f"{_AGENT_LABEL_FULL[bid]} achieved the highest run-over-run improvement "
            f"(<strong>+{bdelta:.2f}</strong>). "
            f"The reflection that produced this change may contain patterns transferable to other agents.",
            f'<span style="font-size:11px;font-weight:600;color:#2563EB;">Consider transferring →</span>',
        ))
    else:
        cards.append((
            "#EFF6FF", "#BFDBFE", "#2563EB",
            "Transfer Opportunity",
            "Run more reflection cycles to surface transferable improvements between agents.",
            "",
        ))

    # Card 3: Zero regressions / eval case growth
    n_eval_total = sum(len(get_eval_cases(a)) for a in get_agent_ids())
    cards.append((
        "#F0FDF4", "#86EFAC", "#15803D",
        f"{n_eval_total} Eval Cases — Growing",
        f"Eval dataset has grown to <strong>{n_eval_total} cases</strong> across all agents. "
        f"Each applied reflection adds regression cases that prevent re-introduction of fixed failures.",
        '<span style="font-size:11px;font-weight:600;color:#15803D;">✓ Growing with each cycle</span>',
    ))

    # Card 4: Reflection loop status
    n_applied = len(apply_history)
    cards.append((
        "#F5F3FF", "#DDD6FE", "#7C3AED",
        f"{n_applied} Reflection{'s' if n_applied != 1 else ''} Applied",
        f"Across all agents, <strong>{n_applied} reflection proposal{'s have' if n_applied != 1 else ' has'}</strong> "
        f"been reviewed and applied through the human approval gate. "
        f"Each apply cycle updates the system prompt, skill file, and eval dataset.",
        "",
    ))

    # Card 5: Shared strengths
    if shared_strengths:
        top_s, s_agents = shared_strengths[0]
        s_scores = []
        for aid in s_agents:
            mps = agent_latest.get(aid, {}).get("mean_per_scorer") or {}
            v = mps.get(top_s)
            if v is not None:
                s_scores.append(f"{_AGENT_LABEL_SHORT[aid]}: {float(v):.2f}")
        cards.append((
            "#ECFDF5", "#6EE7B7", "#047857",
            f"Shared Strength: {top_s.replace('_', ' ').title()}",
            f"<strong>{len(s_agents)} agents</strong> consistently score ≥ 0.85 on "
            f"<strong>{top_s.replace('_', ' ')}</strong>. "
            f"This pattern is stable — {', '.join(s_scores)}.",
            '<span style="font-size:11px;font-weight:600;color:#047857;">✓ Protect this in skill files</span>',
        ))
    else:
        cards.append((
            "#ECFDF5", "#6EE7B7", "#047857",
            "Shared Strengths",
            "Run more evaluation cycles to discover shared high-scoring dimensions across agents.",
            "",
        ))

    # Card 6: Pipeline health
    agents_with_runs = len(agent_latest)
    agents_without = len(get_agent_ids()) - agents_with_runs
    if agents_without > 0:
        cards.append((
            "#FFF7ED", "#FED7AA", "#C2410C",
            f"{agents_without} Agent{'s' if agents_without > 1 else ''} Pending First Run",
            f"{agents_without} agent{'s have' if agents_without > 1 else ' has'} not yet completed a campaign run. "
            f"Navigate to the Campaigns page and run the pipeline for each pending agent.",
            f'<span style="font-size:11px;font-weight:600;color:#C2410C;">Action recommended</span>',
        ))
    else:
        cards.append((
            "#F8FAFC", "#E2E8F0", "#475569",
            "All Agents Active",
            f"All {agents_with_runs} configured agents have completed at least one campaign run. "
            f"The reflection loop is available for every agent in the portfolio.",
            '<span style="font-size:11px;font-weight:600;color:#15803D;">✓ Full portfolio active</span>',
        ))

    # Render 3-column grid
    grid_cols = st.columns(3, gap="medium")
    for i, (bg, border, icon_col, title, body, footer) in enumerate(cards):
        with grid_cols[i % 3]:
            footer_html = f'<div style="margin-top:10px;">{footer}</div>' if footer else ""
            st.markdown(
                f"""
                <div style="background:{bg};border:1px solid {border};border-radius:12px;
                            padding:16px;margin-bottom:12px;">
                  <div style="display:flex;gap:12px;align-items:flex-start;">
                    <div style="width:32px;height:32px;border-radius:8px;flex-shrink:0;
                                background:rgba(255,255,255,0.6);display:flex;
                                align-items:center;justify-content:center;">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                           stroke="{icon_col}" stroke-width="2.5" stroke-linecap="round"
                           stroke-linejoin="round">
                        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
                        <polyline points="17 6 23 6 23 12"/>
                      </svg>
                    </div>
                    <div style="flex:1;min-width:0;">
                      <div style="font-size:12px;font-weight:700;color:#0F172A;margin-bottom:6px;">
                        {title}
                      </div>
                      <div style="font-size:11px;color:#475569;line-height:1.6;">{body}</div>
                      {footer_html}
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ── Section 5: Issue + Strength Matrices ─────────────────────────────────────

def _render_matrices(run_index: list[dict]) -> None:
    # Gather latest run per agent
    agent_latest: dict[str, dict] = {}
    for aid in get_agent_ids():
        agent_runs = sorted(
            [r for r in run_index if r.get("agent_id") == aid],
            key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
        )
        if agent_runs:
            agent_latest[aid] = agent_runs[-1]

    if not agent_latest:
        return

    col_issue, col_strength = st.columns(2, gap="medium")

    # ── Issue Matrix ──────────────────────────────────────────────────────────
    with col_issue:
        with st.container(border=True):
            st.markdown(
                """
                <div style="margin-bottom:14px;">
                  <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                              letter-spacing:.08em;margin-bottom:3px;">Issue Matrix</div>
                  <div style="font-size:15px;font-weight:800;color:#0F172A;">Failure Patterns</div>
                  <div style="font-size:11px;color:#94A3B8;margin-top:2px;">
                    Red = below 0.70 · Amber = 0.70–0.79 · Green = ≥ 0.80.
                    <strong style="color:#64748B;">Systemic</strong> = 2+ agents below threshold.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Collect all dims with at least one agent below 0.80
            weak_dims: dict[str, dict[str, float]] = {}
            for aid, latest in agent_latest.items():
                mps = latest.get("mean_per_scorer") or {}
                for d, v in mps.items():
                    fv = float(v)
                    if fv < 0.80:
                        weak_dims.setdefault(d, {})[aid] = fv

            if not weak_dims:
                st.markdown(
                    '<div style="padding:32px 16px;text-align:center;color:#94A3B8;'
                    'font-size:13px;">No dimensions below 0.80 — excellent performance!</div>',
                    unsafe_allow_html=True,
                )
            else:
                agents_ordered = list(agent_latest.keys())
                short_headers = "".join(
                    f'<th style="padding:8px 10px;font-size:10px;font-weight:700;color:#94A3B8;'
                    f'text-transform:uppercase;letter-spacing:.06em;text-align:center;">'
                    f'{_AGENT_LABEL_SHORT[a].split()[0]}</th>'
                    for a in agents_ordered
                )

                rows_html = ""
                for dim, agent_vals in sorted(weak_dims.items(), key=lambda x: min(x[1].values())):
                    label = dim.replace("_", " ").title()
                    n_bad = sum(1 for v in agent_vals.values() if v < 0.80)
                    scope_html = (
                        '<span style="background:#FEE2E2;color:#B91C1C;font-size:10px;font-weight:600;'
                        'padding:2px 7px;border-radius:100px;white-space:nowrap;border:1px solid #FCA5A5;">'
                        '⚠ Systemic</span>'
                        if n_bad >= 2 else
                        '<span style="background:#FEF9C3;color:#92400E;font-size:10px;font-weight:600;'
                        'padding:2px 7px;border-radius:100px;white-space:nowrap;border:1px solid #FDE68A;">'
                        'Partial</span>'
                    )
                    cells = ""
                    for aid in agents_ordered:
                        v = agent_latest.get(aid, {}).get("mean_per_scorer", {}).get(dim)
                        if v is not None:
                            fv = float(v)
                            bg = _dim_bg(fv)
                            col = _dim_color(fv)
                            cells += (
                                f'<td style="padding:8px 10px;text-align:center;">'
                                f'<span style="background:{bg};color:{col};font-size:11px;'
                                f'font-weight:700;padding:2px 8px;border-radius:100px;">'
                                f'{fv:.2f}</span></td>'
                            )
                        else:
                            cells += '<td style="padding:8px 10px;text-align:center;color:#CBD5E1;font-size:11px;">—</td>'
                    rows_html += f"""
                    <tr style="border-bottom:1px solid #F8FAFC;">
                      <td style="padding:8px 12px;font-size:12px;font-weight:500;color:#334155;
                                 white-space:nowrap;">{label}</td>
                      {cells}
                      <td style="padding:8px 12px;text-align:center;">{scope_html}</td>
                    </tr>
                    """

                st.markdown(
                    f"""
                    <div style="overflow-x:auto;">
                      <table style="width:100%;border-collapse:collapse;">
                        <thead>
                          <tr style="border-bottom:1px solid #E2E8F0;">
                            <th style="padding:8px 12px;font-size:10px;font-weight:700;color:#94A3B8;
                                       text-transform:uppercase;letter-spacing:.06em;text-align:left;">Dimension</th>
                            {short_headers}
                            <th style="padding:8px 12px;font-size:10px;font-weight:700;color:#94A3B8;
                                       text-transform:uppercase;letter-spacing:.06em;text-align:center;">Scope</th>
                          </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                      </table>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── Strength Matrix ───────────────────────────────────────────────────────
    with col_strength:
        with st.container(border=True):
            st.markdown(
                """
                <div style="margin-bottom:14px;">
                  <div style="font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                              letter-spacing:.08em;margin-bottom:3px;">Strength Matrix</div>
                  <div style="font-size:15px;font-weight:800;color:#0F172A;">What's Working — Protect These</div>
                  <div style="font-size:11px;color:#94A3B8;margin-top:2px;">
                    Dimensions where agents consistently score ≥ 0.80.
                    <strong style="color:#64748B;">Shared</strong> = all active agents strong.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Collect all dims with at least one agent above 0.80
            strong_dims: dict[str, dict[str, float]] = {}
            for aid, latest in agent_latest.items():
                mps = latest.get("mean_per_scorer") or {}
                for d, v in mps.items():
                    fv = float(v)
                    if fv >= 0.80:
                        strong_dims.setdefault(d, {})[aid] = fv

            if not strong_dims:
                st.markdown(
                    '<div style="padding:32px 16px;text-align:center;color:#94A3B8;'
                    'font-size:13px;">Run more evaluation cycles to identify shared strengths.</div>',
                    unsafe_allow_html=True,
                )
            else:
                # Show top 5 by avg value, showing bars per agent
                top_strong = sorted(
                    strong_dims.items(),
                    key=lambda x: sum(x[1].values()) / len(x[1]),
                    reverse=True,
                )[:5]

                items_html = ""
                for dim, agent_vals in top_strong:
                    label = dim.replace("_", " ").title()
                    n_agents = len(agent_latest)
                    n_strong = len(agent_vals)
                    is_shared = n_strong >= n_agents
                    scope_badge = (
                        '<span style="background:#DCFCE7;color:#15803D;font-size:10px;font-weight:600;'
                        'padding:1px 7px;border-radius:100px;border:1px solid #A7F3D0;">✓ Shared</span>'
                        if is_shared else
                        '<span style="background:#EEF2FF;color:#2251FF;font-size:10px;font-weight:600;'
                        'padding:1px 7px;border-radius:100px;border:1px solid #C7D2FE;">→ Partial</span>'
                    )

                    bars = ""
                    for aid in agent_latest:
                        v = agent_vals.get(aid)
                        short = _AGENT_LABEL_SHORT[aid].split()[0]
                        cfg = AGENTS[aid]
                        if v is not None:
                            pct = int(float(v) * 100)
                            bars += (
                                f'<div style="flex:1;">'
                                f'<div style="font-size:10px;color:#94A3B8;margin-bottom:3px;">{short}</div>'
                                f'<div style="height:7px;background:#F1F5F9;border-radius:100px;overflow:hidden;">'
                                f'<div style="height:100%;width:{pct}%;background:#34D399;border-radius:100px;"></div></div>'
                                f'<div style="font-size:10px;font-weight:700;color:#15803D;margin-top:2px;">{float(v):.2f}</div>'
                                f'</div>'
                            )
                        else:
                            bars += (
                                f'<div style="flex:1;">'
                                f'<div style="font-size:10px;color:#94A3B8;margin-bottom:3px;">{short}</div>'
                                f'<div style="height:7px;background:#F1F5F9;border-radius:100px;"></div>'
                                f'<div style="font-size:10px;color:#CBD5E1;margin-top:2px;">n/a</div>'
                                f'</div>'
                            )

                    items_html += f"""
                    <div style="margin-bottom:16px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <span style="font-size:12px;font-weight:600;color:#0F172A;">{label}</span>
                        {scope_badge}
                      </div>
                      <div style="display:flex;gap:10px;">{bars}</div>
                    </div>
                    """

                st.markdown(items_html, unsafe_allow_html=True)


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    """Render the Org Overview page."""
    render_nav("org_overview")

    run_index = get_run_index()
    apply_history = get_apply_history()

    # Compute summary stats
    scores = {
        aid: get_latest_score_for_agent(aid)
        for aid in get_agent_ids()
    }
    valid_scores = [s for s in scores.values() if s is not None]
    portfolio_avg = sum(valid_scores) / len(valid_scores) if valid_scores else None
    active_agents = len(valid_scores)
    n_reflections = len(apply_history)
    n_eval_cases = sum(len(get_eval_cases(a)) for a in get_agent_ids())

    # Avg lift per reflection across all agents
    avg_lift: float | None = None
    lifts = []
    for aid in get_agent_ids():
        agent_runs = sorted(
            [r for r in run_index if r.get("agent_id") == aid],
            key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
        )
        if len(agent_runs) >= 2:
            s1 = float(agent_runs[0].get("mean_score") or 0)
            s2 = float(agent_runs[-1].get("mean_score") or 0)
            if s1 > 0:
                lifts.append(s2 - s1)
    if lifts:
        avg_lift = sum(lifts) / len(lifts)

    _render_hero(list(scores.keys()))
    _render_kpis(portfolio_avg, active_agents, n_reflections, n_eval_cases, avg_lift)
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    _render_leaderboard(run_index)
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    _render_charts(run_index)
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    _render_insights(run_index, apply_history)
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    _render_matrices(run_index)
