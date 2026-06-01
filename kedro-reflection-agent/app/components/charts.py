"""Plotly chart factories for the Reflection Hub dashboard.

All figures use a clean white style matching the mockup.
Return go.Figure (or None when there's no data to plot).
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go


# ── Color helpers ─────────────────────────────────────────────────────────────

def _score_color(value: float) -> str:
    if value >= 0.85:
        return "#22C55E"
    if value >= 0.70:
        return "#F59E0B"
    return "#EF4444"


# ── Score progression line chart ──────────────────────────────────────────────

def score_progression_chart(run_index: list[dict], agent_id: str) -> go.Figure | None:
    """Line chart: x=run_id, y=mean_score, with reflection events marked."""
    agent_runs = [r for r in run_index if r.get("agent_id") == agent_id]
    if not agent_runs:
        return None

    agent_runs = sorted(agent_runs, key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)))

    run_ids = [r["run_id"] for r in agent_runs]
    scores = [float(r.get("mean_score") or 0) * 100 for r in agent_runs]
    reflection_runs = [r["run_id"] for r in agent_runs if r.get("reflection_applied")]

    fig = go.Figure()

    # Main line
    fig.add_trace(
        go.Scatter(
            x=run_ids,
            y=scores,
            mode="lines+markers",
            name="Mean score",
            line=dict(color="#2251FF", width=2.5),
            marker=dict(
                size=[10 if r in reflection_runs else 7 for r in run_ids],
                color=[
                    "#2251FF" if r in reflection_runs else "#FFFFFF" for r in run_ids
                ],
                line=dict(color="#2251FF", width=2),
            ),
            hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}%<extra></extra>",
        )
    )

    # Vertical dashed lines at reflection events
    for run_id in reflection_runs:
        if run_id in run_ids:
            fig.add_vline(
                x=run_ids.index(run_id),
                line=dict(dash="dash", color="#8B5CF6", width=1.5),
                annotation_text="Reflection",
                annotation_font=dict(size=10, color="#8B5CF6"),
            )

    # Passing threshold line
    threshold_vals = [float(r.get("passing_threshold") or 0.92) * 100 for r in agent_runs]
    if threshold_vals:
        fig.add_hline(
            y=threshold_vals[0],
            line=dict(dash="dot", color="#94A3B8", width=1),
            annotation_text=f"Threshold {threshold_vals[0]:.0f}%",
            annotation_font=dict(size=10, color="#94A3B8"),
        )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=260,
        margin=dict(l=0, r=0, t=16, b=0),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=12, color="#64748B"),
            title=None,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            range=[0, 105],
            ticksuffix="%",
            tickfont=dict(size=12, color="#64748B"),
            title=None,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12),
        ),
        font=dict(family="Inter, sans-serif"),
    )
    return fig


# ── Dimension horizontal bar chart ────────────────────────────────────────────

def dimension_bars_chart(mean_per_scorer: dict[str, float]) -> go.Figure | None:
    """Horizontal bar chart of dimension scores."""
    if not mean_per_scorer:
        return None

    items = sorted(mean_per_scorer.items(), key=lambda x: x[1])
    names = [k.replace("_", " ").title() for k, _ in items]
    values = [float(v) for _, v in items]
    colors = [_score_color(v) for v in values]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker_color=colors,
            text=[f"{v:.0%}" for v in values],
            textposition="outside",
            textfont=dict(size=12, color="#0F172A"),
            hovertemplate="<b>%{y}</b><br>Score: %{x:.1%}<extra></extra>",
        )
    )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=max(200, len(names) * 36 + 40),
        margin=dict(l=0, r=60, t=8, b=0),
        xaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            range=[0, 1.15],
            tickformat=".0%",
            tickfont=dict(size=11, color="#64748B"),
            title=None,
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(size=12, color="#0F172A"),
            title=None,
        ),
        font=dict(family="Inter, sans-serif"),
    )
    return fig


# ── Dimension delta comparison (multi-run) ────────────────────────────────────

def dimension_delta_table_html(runs: list[dict]) -> str:
    """Return HTML for the before/after dimension comparison table.

    Args:
        runs: List of run_index dicts. Expects at least 2 runs with
              mean_per_scorer dicts. Uses first and last run.
    """
    if len(runs) < 2:
        return ""

    sorted_runs = sorted(runs, key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)))
    run1 = sorted_runs[0]
    run2 = sorted_runs[-1]

    dims1: dict[str, float] = run1.get("mean_per_scorer") or {}
    dims2: dict[str, float] = run2.get("mean_per_scorer") or {}
    all_dims = sorted(set(dims1) | set(dims2))

    if not all_dims:
        return ""

    rows = ""
    for dim in all_dims:
        v1 = float(dims1.get(dim, 0))
        v2 = float(dims2.get(dim, 0))
        delta = v2 - v1
        label = dim.replace("_", " ").title()
        bar1_w = int(v1 * 100)
        bar2_w = int(v2 * 100)
        bar1_color = _score_color(v1)
        bar2_color = _score_color(v2)
        delta_color = "#15803D" if delta >= 0 else "#B91C1C"
        delta_sign = f"+{delta:.1%}" if delta >= 0 else f"{delta:.1%}"

        rows += f"""
        <tr>
          <td style="font-size:13px;font-weight:500;color:#0F172A;padding:10px 12px;
                     white-space:nowrap;">{label}</td>
          <td style="padding:10px 8px;min-width:120px;">
            <div style="display:flex;align-items:center;gap:6px;">
              <div style="height:8px;background:#F1F5F9;border-radius:100px;
                          flex:1;overflow:hidden;">
                <div style="height:100%;width:{bar1_w}%;background:{bar1_color};
                            border-radius:100px;"></div>
              </div>
              <span style="font-size:12px;font-weight:600;color:#0F172A;
                           min-width:36px;text-align:right;">{v1:.0%}</span>
            </div>
          </td>
          <td style="padding:10px 8px;min-width:120px;">
            <div style="display:flex;align-items:center;gap:6px;">
              <div style="height:8px;background:#F1F5F9;border-radius:100px;
                          flex:1;overflow:hidden;">
                <div style="height:100%;width:{bar2_w}%;background:{bar2_color};
                            border-radius:100px;"></div>
              </div>
              <span style="font-size:12px;font-weight:600;color:#0F172A;
                           min-width:36px;text-align:right;">{v2:.0%}</span>
            </div>
          </td>
          <td style="padding:10px 12px;text-align:right;">
            <span style="font-size:13px;font-weight:700;color:{delta_color};">{delta_sign}</span>
          </td>
        </tr>
        """

    run1_id = run1.get("run_id", "Run 1")
    run2_id = run2.get("run_id", "Run N")

    return f"""
    <div style="overflow-x:auto;">
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="border-bottom:1px solid #E2E8F0;">
            <th style="font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                       letter-spacing:0.06em;padding:8px 12px;text-align:left;">Dimension</th>
            <th style="font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                       letter-spacing:0.06em;padding:8px 8px;text-align:left;">{run1_id}</th>
            <th style="font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                       letter-spacing:0.06em;padding:8px 8px;text-align:left;">{run2_id}</th>
            <th style="font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;
                       letter-spacing:0.06em;padding:8px 12px;text-align:right;">Delta</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>
    """
