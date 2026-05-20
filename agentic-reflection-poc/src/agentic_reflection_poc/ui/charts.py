"""Plotly charts for the dashboard."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go


def dimension_bar_chart(run1_dims: dict[str, float], run2_dims: dict[str, float]) -> go.Figure:
    keys = sorted(set(run1_dims) | set(run2_dims))
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Run 1", x=keys, y=[run1_dims.get(k, 0) for k in keys], marker_color="#CCCCCC"))
    fig.add_trace(go.Bar(name="Run 2", x=keys, y=[run2_dims.get(k, 0) for k in keys], marker_color="#1A1A1A"))
    fig.update_layout(
        barmode="group",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#1A1A1A"),
        margin=dict(l=20, r=20, t=30, b=20),
        height=320,
        legend=dict(orientation="h"),
    )
    return fig


def failure_tag_chart(tag_counts: dict[str, int]) -> go.Figure:
    df = pd.DataFrame({"tag": list(tag_counts.keys()), "count": list(tag_counts.values())})
    fig = go.Figure(go.Bar(x=df["tag"], y=df["count"], marker_color="#6B6B6B"))
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=280,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


def case_comparison_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def langfuse_daily_traces_chart(daily_rows: list[dict[str, Any]]) -> go.Figure | None:
    if not daily_rows:
        return None
    df = pd.DataFrame(daily_rows)
    if "date" not in df.columns:
        return None
    fig = go.Figure(
        go.Scatter(
            x=df["date"],
            y=df.get("countTraces", df.get("count_traces", 0)),
            mode="lines+markers",
            name="Traces",
            line=dict(color="#1A1A1A"),
        )
    )
    fig.update_layout(
        title="Daily campaign traces",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Date",
        yaxis_title="Trace count",
    )
    return fig


def langfuse_daily_cost_chart(daily_rows: list[dict[str, Any]]) -> go.Figure | None:
    if not daily_rows:
        return None
    df = pd.DataFrame(daily_rows)
    if "date" not in df.columns or "totalCost" not in df.columns:
        return None
    fig = go.Figure(
        go.Bar(x=df["date"], y=df["totalCost"], marker_color="#6B6B6B", name="Cost (USD)")
    )
    fig.update_layout(
        title="Daily LLM cost (USD)",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Date",
        yaxis_title="USD",
    )
    return fig


def langfuse_score_timeseries_chart(rows: list[dict[str, Any]]) -> go.Figure | None:
    if not rows:
        return None
    df = pd.DataFrame(rows)
    time_col = next((c for c in df.columns if "time" in c.lower() or c == "date"), None)
    value_col = next((c for c in df.columns if "value" in c.lower() and "avg" in c.lower()), None)
    if not time_col or not value_col:
        # metrics API may return e.g. time_dimension_day + value_avg
        time_col = df.columns[0]
        value_col = df.columns[-1]
    fig = go.Figure(
        go.Scatter(
            x=df[time_col],
            y=pd.to_numeric(df[value_col], errors="coerce"),
            mode="lines+markers",
            name="Avg case_total",
            line=dict(color="#1A1A1A"),
        )
    )
    fig.update_layout(
        title="Average case_total score (Langfuse)",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Day",
        yaxis_title="Score",
    )
    return fig
