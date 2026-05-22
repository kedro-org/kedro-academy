"""Embedded observability panels (Kedro-Viz, Langfuse)."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from app import charts, langfuse_analytics
from app.kedro_viz_server import VizStatus, ensure_kedro_viz_running, kedro_viz_url

DEFAULT_LANGFUSE_HOST = "https://cloud.langfuse.com"
_PLACEHOLDERS = {"", "REPLACE_ME"}

STEP1_PIPELINES: list[tuple[str, str]] = [
    ("campaign", "Campaign"),
    ("evaluation", "Evaluation"),
]
STEP2_PIPELINES: list[tuple[str, str]] = [
    ("reflection", "Reflection"),
    ("apply", "Apply"),
]


def _load_credentials() -> dict:
    try:
        from kedro.config import OmegaConfigLoader
        return OmegaConfigLoader(conf_source="conf")["credentials"]
    except Exception:  # noqa: BLE001
        return {}


def _is_set(value: str | None) -> bool:
    return bool(value and str(value).strip() not in _PLACEHOLDERS)


def langfuse_credentials() -> dict:
    return _load_credentials().get("langfuse_credentials", {})


def langfuse_configured() -> bool:
    creds = langfuse_credentials()
    return _is_set(creds.get("public_key")) and _is_set(creds.get("secret_key"))


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
    """Horizontal pipeline picker + full-width Kedro-Viz iframe."""
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


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_langfuse_analytics() -> dict:
    creds = langfuse_credentials()
    traces, total = langfuse_analytics.fetch_traces(creds)
    daily = langfuse_analytics.fetch_daily_metrics(creds)
    score_avgs = langfuse_analytics.fetch_score_averages(creds)
    token_usage = langfuse_analytics.fetch_token_usage_by_model(creds)
    return {"traces": traces, "total": total, "daily": daily, "score_avgs": score_avgs, "token_usage": token_usage}


def render_langfuse_panel(
    *,
    title: str = "Langfuse",
    show_all_traces_link: bool = True,
    key_prefix: str = "lf",
) -> None:
    """Langfuse observability — metrics charts + recent trace links."""
    st.markdown(f"**{title}**")

    if not langfuse_configured():
        st.caption(
            "Configure `langfuse_credentials` in `conf/local/credentials.yml` "
            "to enable Langfuse UI links and charts."
        )
        with st.expander("Self-hosting Langfuse locally", expanded=False):
            st.markdown(
                "Run a local Langfuse instance with Docker:\n"
                "```bash\n"
                "git clone https://github.com/langfuse/langfuse.git\n"
                "cd langfuse\n"
                "docker compose up -d\n"
                "```\n"
                "Then set `host: http://localhost:3000` in `conf/local/credentials.yml`. "
                "No API rate limits apply to a self-hosted instance."
            )
        return

    project_url = langfuse_project_url()
    traces_url = langfuse_traces_url()
    c1, c2 = st.columns(2)
    with c1:
        if project_url:
            st.link_button("Open Langfuse project ↗", project_url, width="stretch")
    with c2:
        if show_all_traces_link and traces_url:
            st.link_button("View all traces ↗", traces_url, width="stretch")

    st.divider()
    data = _fetch_langfuse_analytics()
    total = data["total"]
    api_traces = data["traces"]
    daily = data["daily"]
    score_avgs = data["score_avgs"]
    token_usage = data["token_usage"]

    if total == 0:
        st.caption("No traces found in Langfuse yet — run the campaign pipeline first.")
        return

    # Top metrics row
    c1, c2, c3 = st.columns(3)
    c1.metric("Total traces", total)
    if daily:
        day = daily[0]
        c2.metric("LLM cost (today)", f"${day.get('totalCost', 0):.4f}")
        c3.metric("Observations (today)", day.get("countObservations", 0))

    # Score averages bar chart
    fig_scores = charts.langfuse_score_averages_chart(score_avgs)
    if fig_scores:
        st.plotly_chart(fig_scores, width="stretch", key=f"{key_prefix}_score_avgs")

    # Token usage by model (from /api/public/metrics)
    fig_tokens = charts.langfuse_token_usage_chart(token_usage)
    if fig_tokens:
        st.plotly_chart(fig_tokens, width="stretch", key=f"{key_prefix}_token_usage")

    # Daily activity charts
    fig_traces_chart = charts.langfuse_daily_traces_chart(daily)
    fig_cost = charts.langfuse_daily_cost_chart(daily)
    col_a, col_b = st.columns(2)
    with col_a:
        if fig_traces_chart:
            st.plotly_chart(fig_traces_chart, width="stretch", key=f"{key_prefix}_daily_traces")
    with col_b:
        if fig_cost:
            st.plotly_chart(fig_cost, width="stretch", key=f"{key_prefix}_daily_cost")

    # Recent trace links
    creds = langfuse_credentials()
    if api_traces:
        with st.expander(f"Recent traces ({min(len(api_traces), 20)} shown)", expanded=False):
            for t in api_traces[:20]:
                tid = t.get("id", "")
                name = t.get("name") or tid
                ts = (t.get("timestamp") or "")[:19].replace("T", " ")
                url = langfuse_analytics.trace_url(creds, tid)
                cols = st.columns([3, 1])
                cols[0].write(f"**{name}**")
                cols[0].caption(ts)
                cols[1].link_button("Open ↗", url, width="stretch")


def render_horizontal_tabs(
    labels: list[str],
    panels: list[Callable[[], None]],
) -> None:
    """Render horizontal Streamlit tabs; each panel is a zero-arg callable."""
    if len(labels) != len(panels):
        raise ValueError("labels and panels must have the same length")
    tabs = st.tabs(labels)
    for tab, panel in zip(tabs, panels, strict=True):
        with tab:
            panel()
