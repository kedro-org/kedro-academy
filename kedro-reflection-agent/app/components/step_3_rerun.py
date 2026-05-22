"""Step 3 — Re-run campaign with improved prompt/skill and compare."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app import runner
from app import ui_components as ui
from app import embeds, charts
from app.state import DemoState, save_demo_state, transition, DEFAULT_STATE_PATH

_RUN_ID_1 = "run_1"
_RUN_ID_2 = "run_2"
_DATA = Path("data")
_OUTPUTS = _DATA / "outputs" / "runs"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

@st.cache_data
def _load_aggregate(run_id: str) -> dict | None:
    p = _OUTPUTS / run_id / "aggregate_scores.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@st.cache_data
def _load_emails(run_id: str) -> list[dict]:
    d = _OUTPUTS / run_id / "emails"
    if not d.exists():
        return []
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("*.json"))]


@st.cache_data
def _load_scores_by_case(run_id: str) -> dict[str, dict]:
    p = _OUTPUTS / run_id / "per_case_scores.json"
    if not p.exists():
        return {}
    return {s["case_id"]: s for s in json.loads(p.read_text(encoding="utf-8"))}


@st.cache_data
def _load_customers() -> dict[str, dict]:
    p = _DATA / "seed" / "customers.json"
    return {c["customer_id"]: c for c in json.loads(p.read_text(encoding="utf-8"))} if p.exists() else {}


@st.cache_data
def _load_products() -> dict[str, dict]:
    p = _DATA / "seed" / "products.json"
    return {prod["product_id"]: prod for prod in json.loads(p.read_text(encoding="utf-8"))} if p.exists() else {}


def _load_trace_metadata(run_id: str) -> list[dict]:
    p = _OUTPUTS / run_id / "trace_metadata.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Step root
# ---------------------------------------------------------------------------

def render(demo: DemoState) -> None:
    done = demo.state == "run_2_done"
    ui.step_heading(
        "STEP 3 — Re-run & Compare",
        done=done,
        muted=demo.state not in ("applied", "run_2_done"),
    )

    with ui.story_section("Pipeline"):
        embeds.render_kedro_viz_pipeline_picker(
            project_root=str(runner.PROJECT_ROOT),
            pipelines=embeds.STEP1_PIPELINES,
            default_pipeline_id="campaign",
            height=520,
            session_key="viz_pipeline_step3",
        )

    with ui.story_section("Run"):
        st.code(
            'kedro run --pipelines campaign --params "run_id=run_2"\n'
            'kedro run --pipelines evaluation --params "run_id=run_2"',
            language="bash",
        )
        run_clicked = st.button(
            "Re-run Generate & Evaluate",
            disabled=not demo.can_run_agent_step3(),
            type="primary",
            key="step3_run",
        )
        log_target = ui.pipeline_log_slot()

        if run_clicked:
            log_lines: list[str] = []
            st.session_state["step3_logs"] = log_lines

            def _log(line: str) -> None:
                log_lines.append(line)
                ui.update_pipeline_log(log_target, log_lines)

            with st.spinner("Running campaign and evaluation for run_2…"):
                ok, _ = runner.run_campaign(_RUN_ID_2, on_log=_log)

            if ok:
                st.cache_data.clear()
                new_demo = transition(demo, "run_2_done", run_2_id=_RUN_ID_2)
                save_demo_state(new_demo, DEFAULT_STATE_PATH)
                st.rerun()
            else:
                st.error("Pipeline failed — see log above.")

    if demo.state not in ("applied", "run_2_done"):
        st.caption("Approve and apply in Step 2 before re-running.")
        return

    if not done:
        st.caption("Press re-run above, then the tabs below will populate.")
        return

    run1 = _load_aggregate(_RUN_ID_1)
    run2 = _load_aggregate(_RUN_ID_2)
    scores1 = _load_scores_by_case(_RUN_ID_1)
    scores2 = _load_scores_by_case(_RUN_ID_2)
    emails1 = {e["case_id"]: e for e in _load_emails(_RUN_ID_1)}
    emails2 = {e["case_id"]: e for e in _load_emails(_RUN_ID_2)}
    customers = _load_customers()
    products = _load_products()
    traces1 = _load_trace_metadata(_RUN_ID_1)
    traces2 = _load_trace_metadata(_RUN_ID_2)

    def tab_logs() -> None:
        lines = st.session_state.get("step3_logs") or []
        if lines:
            st.code("".join(lines[-200:]), language="log")
        else:
            st.caption("Pipeline logs appear here after you run a step.")

    def tab_compare() -> None:
        if not run1 or not run2:
            st.caption("Aggregate scores not found for one or both runs.")
            return

        ui.score_headline(run1["mean_total"], run2["mean_total"])

        if run1.get("mean_per_scorer") and run2.get("mean_per_scorer"):
            st.plotly_chart(
                charts.dimension_bar_chart(
                    run1["mean_per_scorer"],
                    run2["mean_per_scorer"],
                ),
                width="stretch",
                key="step3_dimension_bar_chart",
            )

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Pass rate",
            f"{run2['pass_rate']:.0%}",
            delta=f"{(run2['pass_rate'] - run1['pass_rate']):+.0%}",
        )
        c2.metric(
            "Mean score",
            f"{run2['mean_total'] * 10:.2f} / 10",
            delta=f"{(run2['mean_total'] - run1['mean_total']) * 10:+.2f}",
        )
        c3.metric(
            "Passing cases",
            f"{run2['n_passing']} / {run2['n_cases']}",
            delta=run2["n_passing"] - run1["n_passing"],
        )

        with st.expander("Per-case score deltas", expanded=True):
            rows = []
            for cid, sc1 in scores1.items():
                sc2 = scores2.get(cid, {})
                rows.append({
                    "case_id": cid,
                    "run_1": round(sc1.get("mean_score", 0) * 10, 2),
                    "run_2": round(sc2.get("mean_score", 0) * 10, 2),
                    "delta": round((sc2.get("mean_score", 0) - sc1.get("mean_score", 0)) * 10, 2),
                })
            st.dataframe(
                pd.DataFrame(rows).sort_values("delta", ascending=False),
                width="stretch",
                hide_index=True,
            )

        with st.expander("Email before/after — word-level diff (worst Run 1 cases)", expanded=True):
            worst = sorted(scores1.items(), key=lambda kv: kv[1].get("mean_score", 1.0))[:3]
            for cid, sc1 in worst:
                e1 = emails1.get(cid, {})
                e2 = emails2.get(cid, {})
                sc2 = scores2.get(cid, {})
                cust = customers.get(e1.get("customer_id", ""), {})
                prod = products.get(e1.get("product_id", ""), {})
                failure_tags = [
                    ev["name"]
                    for ev in sc1.get("evaluations", [])
                    if ev.get("value", 1.0) < 1.0
                ]
                ui.email_diff_cards(
                    company=cust.get("company_name", e1.get("customer_id", cid)),
                    product=prod.get("name", e1.get("product_id", "")),
                    subject1=e1.get("subject", ""),
                    body1=e1.get("body", ""),
                    score1=sc1.get("mean_score"),
                    failure_tags1=failure_tags,
                    subject2=e2.get("subject", ""),
                    body2=e2.get("body", ""),
                    score2=sc2.get("mean_score"),
                )
                st.divider()

    def tab_langfuse() -> None:
        embeds.render_langfuse_panel(title="Langfuse")
        if traces1 or traces2:
            st.divider()
            embeds.render_trace_comparison(traces1, traces2)

    with ui.story_section("Observe & results"):
        embeds.render_horizontal_tabs(
            ["Run logs", "Compare", "Langfuse"],
            [tab_logs, tab_compare, tab_langfuse],
        )
