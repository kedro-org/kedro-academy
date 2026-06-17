"""Stage 1: Campaign & Evaluate component."""

from __future__ import annotations

import re

import streamlit as st

from app.formatting import pass_rate_explainer_html
from app.components.charts import dimension_bars_chart
from app.data_loader import get_aggregate_scores, get_run_index

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[mK]")

# JS injected via st.iframe to click the Run Logs tab in the nearest
# preceding tablist — uses document position so it targets the right stage
# even when multiple stages with sub-tabs are rendered simultaneously.
_SELECT_RUN_LOGS_JS = (
    "<script>(function(){"
    "var d=window.parent.document;"
    "var me=Array.from(d.querySelectorAll('iframe')).find(function(f){return f.contentWindow===window;});"
    "if(!me)return;"
    "var tls=Array.from(d.querySelectorAll('[role=\"tablist\"]'));"
    "var cl=null;"
    "tls.forEach(function(tl){if(me.compareDocumentPosition(tl)&Node.DOCUMENT_POSITION_PRECEDING){cl=tl;}});"
    "if(!cl)return;"
    "var btn=Array.from(cl.querySelectorAll('button[role=\"tab\"]')).find(function(t){return t.textContent.includes('Run Logs');});"
    "if(btn)btn.click();"
    "})();</script>"
)


def _clean_log(lines: list[str]) -> str:
    raw = "".join(lines[-200:])
    return _ANSI_ESCAPE.sub("", raw)


def _kpi_card(label: str, value: str, delta: str = "", delta_positive: bool = True) -> str:
    delta_color = "#15803D" if delta_positive else "#B91C1C"
    delta_html = (
        f'<div style="font-size:12px;font-weight:600;color:{delta_color};margin-top:4px;">'
        f"{delta}</div>"
        if delta
        else ""
    )
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {delta_html}
    </div>
    """


def render_stage_campaign(
    agent_id: str,
    run_id: str | None,
    demo_state: object,
) -> None:
    """Render Stage 1: Campaign & Evaluate."""

    # ── Command strip ─────────────────────────────────────────────────────────
    run_id_display = run_id or "run_1"
    cmd = (
        f"kedro run --pipelines campaign,evaluation "
        f"--params agent_id={agent_id},run_id={run_id_display}"
    )

    col_cmd, col_btn = st.columns([5, 1])
    with col_cmd:
        st.markdown(
            f"""
            <div class="command-strip">
              <div style="flex:1;min-width:0;">
                <div style="font-size:10.5px;color:#94A3B8;margin-bottom:6px;">
                  Generate outreach emails → evaluate on writing quality, personalisation,
                  groundedness, CTA
                </div>
                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                  <span style="color:#4ADE80;font-family:monospace;font-size:13px;">$</span>
                  <span class="command-text">{cmd}</span>
                </div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">
                  <span class="command-pill">dataset: {agent_id}_eval</span>
                  <span class="command-pill">skill: {agent_id}_style.md</span>
                  <span class="command-pill">judge: gpt-4o</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown('<div style="padding-top:4px;">', unsafe_allow_html=True)
        run_clicked = st.button(
            "▶ Run",
            key=f"run_campaign_{agent_id}",
            type="primary",
            width="stretch",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Sub-tabs ──────────────────────────────────────────────────────────────
    _logs_key = f"show_run_logs_{agent_id}"
    if run_clicked:
        st.session_state[_logs_key] = True
    _show_logs = st.session_state.pop(_logs_key, False)
    tab_viz, tab_logs, tab_langfuse = st.tabs(["⊞ Kedro-Viz", ">_ Run Logs", "∿ Langfuse"])
    if _show_logs:
        st.iframe(_SELECT_RUN_LOGS_JS, height=1)

    # ── Kedro-Viz tab ─────────────────────────────────────────────────────────
    with tab_viz:
        _render_kedro_viz(agent_id)

    # ── Run Logs tab ──────────────────────────────────────────────────────────
    with tab_logs:
        if run_clicked:
            from app import runner
            log_lines: list[str] = []
            log_placeholder = st.empty()

            def on_log(line: str) -> None:
                log_lines.append(line)
                st.session_state[f"campaign_logs_{agent_id}"] = log_lines.copy()
                clean = _ANSI_ESCAPE.sub("", "".join(log_lines[-80:]))
                log_placeholder.code(clean, language="log")

            with st.spinner("Running campaign + evaluation pipeline…"):
                ok, _ = runner.run_campaign(run_id_display, agent_id, on_log=on_log)

            if ok:
                st.success("Campaign + evaluation completed successfully.")
            else:
                st.error("Pipeline failed — check logs above.")
            st.session_state[_logs_key] = True
            st.rerun()
        else:
            log_lines = st.session_state.get(f"campaign_logs_{agent_id}", [])
            if log_lines:
                active_filter = st.segmented_control(
                    "Filter",
                    options=["All", "INFO", "ERROR"],
                    default="All",
                    key="log_filter_campaign",
                    label_visibility="collapsed",
                )
                if active_filter == "INFO":
                    filtered = [l for l in log_lines if "INFO" in l]
                elif active_filter == "ERROR":
                    filtered = [l for l in log_lines if "ERROR" in l]
                else:
                    filtered = log_lines
                clean = _clean_log(filtered)
                if clean:
                    st.code(clean, language="log")
                else:
                    st.caption("No matching log lines for this filter.")

    # ── Langfuse tab ─────────────────────────────────────────────────────────
    with tab_langfuse:
        agg = get_aggregate_scores(agent_id, run_id or "") if run_id else None

        if agg is None:
            st.info("Run the campaign pipeline to see Langfuse analytics here.")
        else:
            mean_score = float(agg.get("mean_total") or agg.get("mean_score") or 0)
            n_cases = int(agg.get("n_cases") or 0)
            n_passing = int(agg.get("n_passing") or 0)
            pass_rate = float(agg.get("pass_rate") or 0)
            run_meta = next(
                (
                    r
                    for r in get_run_index()
                    if r.get("agent_id") == agent_id and r.get("run_id") == run_id
                ),
                {},
            )
            n_errors = int(run_meta.get("n_errors") or 0)
            langfuse_url = agg.get("langfuse_experiment_url") or agg.get("dataset_run_url")

            # 4 KPI cards
            kpi_cols = st.columns(4)
            with kpi_cols[0]:
                st.markdown(
                    _kpi_card("Total Traces", str(n_cases)),
                    unsafe_allow_html=True,
                )
            with kpi_cols[1]:
                st.markdown(
                    _kpi_card("Pass Rate", f"{n_passing}/{n_cases} ({pass_rate:.0%})"),
                    unsafe_allow_html=True,
                )
            with kpi_cols[2]:
                st.markdown(
                    _kpi_card("Pipeline Errors", str(n_errors), delta_positive=n_errors == 0),
                    unsafe_allow_html=True,
                )
            with kpi_cols[3]:
                st.markdown(
                    _kpi_card("Avg Score", f"{mean_score:.1%}"),
                    unsafe_allow_html=True,
                )

            stored_threshold = agg.get("passing_threshold")
            if stored_threshold is not None:
                stored_threshold = float(stored_threshold)
            st.markdown(
                pass_rate_explainer_html(agent_id, stored_threshold=stored_threshold),
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

            # Dimension bars
            mean_per_scorer: dict = agg.get("mean_per_scorer") or {}
            if mean_per_scorer:
                st.markdown(
                    '<div style="font-size:13px;font-weight:600;color:#0F172A;margin-bottom:8px;">'
                    "Dimension Scores</div>",
                    unsafe_allow_html=True,
                )
                fig = dimension_bars_chart(mean_per_scorer)
                if fig:
                    st.plotly_chart(
                        fig,
                        width="stretch",
                        config={"displayModeBar": False},
                    )

            # Langfuse link
            if langfuse_url:
                st.markdown(
                    f"""
                    <div style="margin-top:12px;">
                      <a href="{langfuse_url}" target="_blank"
                         style="font-size:13px;color:#2251FF;font-weight:600;
                                text-decoration:none;">
                        ↗ View dataset run in Langfuse
                      </a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Recent traces (collapsible)
            per_case = agg.get("per_case_scores") or []
            if per_case:
                with st.expander("Recent traces", expanded=False):
                    for case in per_case[:10]:
                        case_id = case.get("case_id", "—")
                        score = float(case.get("case_total") or case.get("score") or 0)
                        passed = bool(case.get("passed", score >= 0.7))
                        status_color = "#15803D" if passed else "#B91C1C"
                        status_label = "PASS" if passed else "FAIL"
                        st.markdown(
                            f"""
                            <div style="display:flex;justify-content:space-between;
                                        align-items:center;padding:8px 0;
                                        border-bottom:1px solid #F1F5F9;">
                              <span style="font-size:13px;color:#0F172A;
                                           font-family:monospace;">{case_id}</span>
                              <div style="display:flex;align-items:center;gap:10px;">
                                <span style="font-size:13px;font-weight:600;color:#0F172A;">
                                  {score:.1%}
                                </span>
                                <span style="background:{status_color}18;color:{status_color};
                                             font-size:11px;font-weight:700;padding:2px 7px;
                                             border-radius:100px;">{status_label}</span>
                              </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )


def _render_kedro_viz(agent_id: str) -> None:
    from app.components.kedro_viz_tab import render_kedro_viz
    render_kedro_viz(agent_id, ["campaign", "evaluation"], stage_key="campaign")
