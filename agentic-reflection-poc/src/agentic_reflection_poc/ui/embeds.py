"""Embedded observability panels (Kedro-Viz, Langfuse)."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from kedro.config import OmegaConfigLoader
from agentic_reflection_poc.ui.langfuse_analytics import (
    fetch_case_score_timeseries,
    fetch_daily_metrics,
    fetch_trace_count_timeseries,
)
from agentic_reflection_poc.ui import charts
from agentic_reflection_poc.ui.kedro_viz_server import VizStatus, ensure_kedro_viz_running, kedro_viz_url

DEFAULT_LANGFUSE_HOST = "https://cloud.langfuse.com"
_PLACEHOLDERS = {"", "REPLACE_ME"}


def _load_credentials() -> dict:
    try:
        return OmegaConfigLoader(conf_source="conf")["credentials"]
    except Exception:  # noqa: BLE001
        return {}


def _is_set(value: str | None) -> bool:
    return bool(value and str(value).strip() not in _PLACEHOLDERS)


def langfuse_credentials() -> dict:
    return _load_credentials().get("langfuse_credentials", {})


def openai_api_key_configured() -> bool:
    return _is_set(_load_credentials().get("openai_credentials", {}).get("api_key"))


def langfuse_configured() -> bool:
    creds = langfuse_credentials()
    return _is_set(creds.get("public_key")) and _is_set(creds.get("secret_key"))

STEP1_PIPELINES: list[tuple[str, str]] = [
    ("agent_run", "Agent run"),
    ("evaluation", "Evaluation"),
]
STEP2_PIPELINES: list[tuple[str, str]] = [
    ("reflection", "Reflection"),
    ("apply", "Apply"),
]


def render_credentials_status() -> None:
    st.markdown("##### Configuration")
    if openai_api_key_configured():
        st.success("OpenAI API key is configured.")
    else:
        st.error(
            "OpenAI API key missing. Add `openai_credentials.api_key` to "
            "`conf/local/credentials.yml`, or enable **Mock LLM mode** below."
        )
    if langfuse_configured():
        st.success("Langfuse credentials are configured.")
    else:
        st.warning(
            "Langfuse credentials not set. Tracing will fail until you add "
            "`langfuse_credentials` to `conf/local/credentials.yml`."
        )


def render_kedro_viz_status(project_root: str) -> VizStatus:
    status = ensure_kedro_viz_running(project_root)
    if status == "failed":
        err = st.session_state.get("kedro_viz_error", "unknown error")
        st.caption(f"Kedro-Viz failed: {err[:80]}")
    elif status == "unavailable":
        st.caption("Kedro-Viz unavailable (run `pip install kedro-viz`).")
    return status


def render_kedro_viz_panel(
    *,
    height: int = 520,
    project_root: str | None = None,
    pipeline_id: str | None = None,
    caption: str | None = None,
) -> None:
    if caption:
        st.caption(caption)
    root = project_root or "."
    status = ensure_kedro_viz_running(root)
    url = kedro_viz_url(pipeline_id=pipeline_id)
    if status == "ready":
        st.iframe(url, height=height)
        st.link_button("Open Kedro-Viz in new tab ↗", url, width="content")
    elif status == "starting":
        st.info("Kedro-Viz is starting in the background (first launch may take ~10s). Refresh the page.")
    else:
        st.warning(
            "Could not start Kedro-Viz. Run `pip install kedro-viz` and restart the app, "
            "or start manually: `kedro viz run`."
        )
        err = st.session_state.get("kedro_viz_error")
        if err:
            st.code(err, language="text")


def render_kedro_viz_pipeline_picker(
    *,
    project_root: str,
    pipelines: list[tuple[str, str]],
    default_pipeline_id: str,
    height: int = 560,
    session_key: str,
) -> None:
    """Horizontal picker + full-width iframe focused on one Kedro pipeline."""
    ids = [pid for pid, _ in pipelines]
    labels = {pid: label for pid, label in pipelines}
    st.session_state.setdefault(session_key, default_pipeline_id)

    choice = st.radio(
        "Pipeline",
        options=ids,
        format_func=lambda pid: labels[pid],
        horizontal=True,
        key=session_key,
        label_visibility="collapsed",
    )
    render_kedro_viz_panel(
        height=height,
        project_root=project_root,
        pipeline_id=choice,
        caption=f"Pipeline: `{choice}`",
    )


def langfuse_project_url() -> str | None:
    creds = langfuse_credentials()
    host = (creds.get("host") or DEFAULT_LANGFUSE_HOST).rstrip("/")
    project_id = creds.get("project_id", "").strip()
    if project_id:
        return f"{host}/project/{project_id}"
    return f"{host}/"


def langfuse_traces_url() -> str | None:
    creds = langfuse_credentials()
    host = (creds.get("host") or DEFAULT_LANGFUSE_HOST).rstrip("/")
    project_id = creds.get("project_id", "").strip()
    if project_id:
        return f"{host}/project/{project_id}/traces"
    return langfuse_project_url()


def render_langfuse_panel(
    trace_metadata: list[dict] | None = None,
    *,
    title: str = "Langfuse",
    show_all_traces_link: bool = True,
) -> None:
    """Langfuse observability via API charts + trace deep-links (no iframe)."""
    st.markdown(f"**{title}**")
    if not langfuse_configured():
        st.warning(
            "Add `langfuse_credentials` (public_key, secret_key, host, project_id) "
            "to `conf/local/credentials.yml`, then re-run the agent."
        )
        return

    creds = langfuse_credentials()
    project_url = langfuse_project_url()
    traces_url = langfuse_traces_url()
    c1, c2 = st.columns(2)
    with c1:
        if project_url:
            st.link_button("Open Langfuse project ↗", project_url, width="stretch")
    with c2:
        if show_all_traces_link and traces_url:
            st.link_button("View all traces ↗", traces_url, width="stretch")

    st.caption(
        "Charts load from the [Langfuse metrics APIs](https://langfuse.com/docs/analytics/daily-metrics-api) "
        "(daily metrics + time-series). Full UI opens in a new tab."
    )

    with st.spinner("Loading Langfuse metrics…"):
        daily = fetch_daily_metrics(creds, days=14)
        score_ts = fetch_case_score_timeseries(creds, days=14)
        if not daily:
            trace_ts = fetch_trace_count_timeseries(creds, days=14)
        else:
            trace_ts = []

    col_a, col_b = st.columns(2)
    with col_a:
        fig = charts.langfuse_daily_traces_chart(daily) or (
            charts.langfuse_score_timeseries_chart(trace_ts) if trace_ts else None
        )
        if fig:
            st.plotly_chart(fig, width="stretch", key=f"lf_traces_{title}")
        else:
            st.caption("No daily trace data yet — run the agent after configuring Langfuse.")
    with col_b:
        cost_fig = charts.langfuse_daily_cost_chart(daily)
        score_fig = charts.langfuse_score_timeseries_chart(score_ts)
        if cost_fig:
            st.plotly_chart(cost_fig, width="stretch", key=f"lf_cost_{title}")
        elif score_fig:
            st.plotly_chart(score_fig, width="stretch", key=f"lf_score_{title}")
        else:
            st.caption("No cost or score time-series yet.")

    if trace_metadata:
        st.divider()
        render_trace_links(trace_metadata, title="Traces from this run")
    else:
        st.info("Run the agent pipeline to populate per-case trace links below.")


def render_trace_links(trace_metadata: list[dict], *, title: str = "Run traces") -> None:
    if not trace_metadata:
        st.caption("No traces recorded yet.")
        return
    st.markdown(f"**{title}**")
    linked = [t for t in trace_metadata if t.get("trace_url")]
    if not linked:
        st.caption("Traces were attempted but no URLs were returned (check pipeline logs).")
        return
    for item in linked:
        cols = st.columns([3, 1])
        cols[0].write(f"**{item.get('company_name', '')}** · {item.get('product_name', '')}")
        cols[0].caption(item.get("case_id", ""))
        url = item.get("trace_url")
        if url:
            cols[1].link_button("Open trace ↗", url, width="stretch")


def render_trace_comparison(traces_run1: list[dict], traces_run2: list[dict]) -> None:
    """Side-by-side trace links for Run 1 vs Run 2."""
    st.markdown("**Trace comparison — Run 1 vs Run 2**")
    if not traces_run1 and not traces_run2:
        st.caption("No trace metadata yet. Re-run Step 3 after Langfuse is configured.")
        return

    by_case_1 = {t.get("case_id"): t for t in traces_run1 if t.get("case_id")}
    by_case_2 = {t.get("case_id"): t for t in traces_run2 if t.get("case_id")}
    case_ids = sorted(set(by_case_1) | set(by_case_2))

    if not case_ids:
        col_a, col_b = st.columns(2)
        with col_a:
            render_trace_links(traces_run1, title="Run 1")
        with col_b:
            render_trace_links(traces_run2, title="Run 2")
        return

    for case_id in case_ids:
        t1 = by_case_1.get(case_id, {})
        t2 = by_case_2.get(case_id, {})
        label = t1.get("company_name") or t2.get("company_name") or case_id
        st.markdown(f"**{label}** · `{case_id}`")
        left, right = st.columns(2)
        with left:
            st.caption("Run 1 (before)")
            _trace_link_cell(t1)
        with right:
            st.caption("Run 2 (after)")
            _trace_link_cell(t2)


def _trace_link_cell(item: dict) -> None:
    if not item:
        st.caption("No trace")
        return
    st.write(item.get("product_name", ""))
    url = item.get("trace_url")
    if url:
        st.link_button("Open trace ↗", url, width="stretch")
    elif item.get("trace_id"):
        st.code(item.get("trace_id"), language=None)


def render_horizontal_tabs(
    labels: list[str],
    panels: list[Callable[[], None]],
) -> None:
    """Render horizontal Streamlit tabs; each panel is a zero-arg callback."""
    if len(labels) != len(panels):
        raise ValueError("labels and panels must have the same length")
    tabs = st.tabs(labels)
    for tab, panel in zip(tabs, panels, strict=True):
        with tab:
            panel()
