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

# ── Portfolio trend (multi-agent) ─────────────────────────────────────────────

_AGENT_COLORS = {
    "b2b_sales": "#2251FF",
    "consumer_mktg": "#8B5CF6",
    "customer_care": "#00C4B4",
}
_AGENT_LABELS = {
    "b2b_sales": "B2B Sales",
    "consumer_mktg": "Cons. Marketing",
    "customer_care": "Customer Care",
}


def portfolio_trend_chart(run_index: list[dict]) -> go.Figure | None:
    """Multi-line chart: one line per agent, x=run sequence, y=mean_score."""
    from collections import defaultdict

    by_agent: dict[str, list[dict]] = defaultdict(list)
    for r in run_index:
        aid = r.get("agent_id")
        if aid and r.get("mean_score") is not None:
            by_agent[aid].append(r)

    if not by_agent:
        return None

    fig = go.Figure()

    for agent_id in ["b2b_sales", "consumer_mktg", "customer_care"]:
        runs = sorted(by_agent.get(agent_id, []),
                      key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)))
        if not runs:
            continue
        color = _AGENT_COLORS.get(agent_id, "#64748B")
        label = _AGENT_LABELS.get(agent_id, agent_id)
        xs = [r.get("run_id", f"run_{i+1}") for i, r in enumerate(runs)]
        ys = [float(r["mean_score"]) for r in runs]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers", name=label,
            line=dict(color=color, width=2),
            marker=dict(size=7, color=color, line=dict(color="white", width=1.5)),
            hovertemplate="<b>%{x}</b><br>Score: %{y:.2f}<extra></extra>",
        ))

    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        height=175, margin=dict(l=0, r=8, t=8, b=0),
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#64748B"), title=None),
        yaxis=dict(
            showgrid=True, gridcolor="#F1F5F9",
            range=[0.5, 1.0],
            tickformat=".2f",
            tickfont=dict(size=10, color="#64748B"), title=None,
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=10), itemwidth=30,
        ),
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def dimension_radar_chart(agent_scores: dict[str, dict[str, float]]) -> go.Figure | None:
    """Radar chart: dimensions on axes, one trace per agent.

    agent_scores: {agent_id: {canonical_dim: score}}
    """
    if not agent_scores:
        return None

    # Canonical radar dimensions (shared across agents)
    dims = ["Writing/Tone", "Personalisation", "CTA/Resolution", "Groundedness", "Compliance"]

    # Map raw scorer names → canonical dim
    _DIM_MAP = {
        "writing_quality": "Writing/Tone",
        "tone": "Writing/Tone",
        "personalization": "Personalisation",
        "personalisation": "Personalisation",
        "cta_present": "CTA/Resolution",
        "urgency_cta": "CTA/Resolution",
        "resolution_clarity": "CTA/Resolution",
        "no_fake_skus": "Groundedness",
        "groundedness": "Groundedness",
        "compliance": "Compliance",
    }

    fig = go.Figure()
    for agent_id in ["b2b_sales", "consumer_mktg", "customer_care"]:
        raw = agent_scores.get(agent_id)
        if not raw:
            continue
        color = _AGENT_COLORS.get(agent_id, "#64748B")
        label = _AGENT_LABELS.get(agent_id, agent_id)

        # Average raw scorers into canonical dims
        buckets: dict[str, list[float]] = {d: [] for d in dims}
        for scorer, val in raw.items():
            canonical = _DIM_MAP.get(scorer)
            if canonical:
                buckets[canonical].append(float(val))
        values = [
            sum(buckets[d]) / len(buckets[d]) if buckets[d] else 0.0
            for d in dims
        ]
        # Close the radar loop
        values_closed = values + [values[0]]
        dims_closed = dims + [dims[0]]

        fig.add_trace(go.Scatterpolar(
            r=values_closed, theta=dims_closed, fill="toself", name=label,
            line=dict(color=color, width=2),
            fillcolor=color.replace(")", ",0.07)").replace("rgb", "rgba") if color.startswith("rgb") else color + "12",
            marker=dict(size=4),
            hovertemplate="<b>%{theta}</b>: %{r:.2f}<extra></extra>",
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0.5, 1.0],
                tickfont=dict(size=9, color="#94A3B8"),
                gridcolor="#F1F5F9", linecolor="#E2E8F0",
                tickvals=[0.6, 0.7, 0.8, 0.9, 1.0],
                ticktext=["0.6", "0.7", "0.8", "0.9", "1.0"],
                showticklabels=True,
            ),
            angularaxis=dict(tickfont=dict(size=10, color="#0F172A"), linecolor="#E2E8F0"),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        height=175,
        margin=dict(l=24, r=24, t=8, b=8),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5,
            font=dict(size=10), itemwidth=30,
        ),
        font=dict(family="Inter, sans-serif"),
        showlegend=True,
    )
    return fig


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
