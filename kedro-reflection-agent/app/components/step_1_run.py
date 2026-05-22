"""Step 1 — Generate emails and evaluate them."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from app import runner
from app import ui_components as ui
from app import embeds, charts
from app.state import DemoState, save_demo_state, transition, DEFAULT_STATE_PATH

_RUN_ID = "run_1"
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
    if not p.exists():
        return {}
    return {c["customer_id"]: c for c in json.loads(p.read_text(encoding="utf-8"))}


@st.cache_data
def _load_products() -> dict[str, dict]:
    p = _DATA / "seed" / "products.json"
    if not p.exists():
        return {}
    return {prod["product_id"]: prod for prod in json.loads(p.read_text(encoding="utf-8"))}


def _compute_failure_tags(scores: dict[str, dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sc in scores.values():
        for ev in sc.get("evaluations", []):
            if ev.get("value", 1.0) < 1.0:
                tag = ev.get("name", "unknown")
                counts[tag] = counts.get(tag, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Step root
# ---------------------------------------------------------------------------

def render(demo: DemoState) -> None:
    done = demo.state != "idle"
    ui.step_heading("STEP 1 — Generate & Evaluate", done=done)

    with ui.story_section("Pipeline"):
        embeds.render_kedro_viz_pipeline_picker(
            project_root=str(runner.PROJECT_ROOT),
            pipelines=embeds.STEP1_PIPELINES,
            default_pipeline_id="campaign",
            height=520,
            session_key="viz_pipeline_step1",
        )

    agg = _load_aggregate(_RUN_ID) if done else None

    with ui.story_section("Run"):
        st.code(
            'kedro run --pipelines campaign --params "run_id=run_1"\n'
            'kedro run --pipelines evaluation --params "run_id=run_1"',
            language="bash",
        )
        c1, c2, c3, c4 = st.columns([2, 0.1, 1, 1])
        with c1:
            run_clicked = st.button(
                "Run Generate & Evaluate",
                disabled=not demo.can_run_agent_step1(),
                type="primary",
                key="step1_run",
            )
        with c3:
            st.metric("Mean score", f"{agg['mean_total'] * 10:.1f}/10" if agg else "—")
        with c4:
            st.metric("Pass rate", f"{agg['pass_rate']:.0%}" if agg else "—")

        log_target = ui.pipeline_log_slot()
        if run_clicked:
            log_lines: list[str] = []
            st.session_state["step1_logs"] = log_lines

            def _log(line: str) -> None:
                log_lines.append(line)
                ui.update_pipeline_log(log_target, log_lines)

            with st.spinner("Running campaign and evaluation for run_1…"):
                ok, _ = runner.run_campaign(_RUN_ID, on_log=_log)

            if ok:
                st.cache_data.clear()
                new_demo = transition(demo, "run_1_done", run_1_id=_RUN_ID)
                save_demo_state(new_demo, DEFAULT_STATE_PATH)
                st.rerun()
            else:
                st.error("Pipeline failed — see log above.")

    if not done:
        st.caption("Complete this step to unlock the tabs below.")
        return

    emails = _load_emails(_RUN_ID)
    scores = _load_scores_by_case(_RUN_ID)
    customers = _load_customers()
    products = _load_products()

    def tab_logs() -> None:
        lines = st.session_state.get("step1_logs") or []
        if lines:
            st.code("".join(lines[-200:]), language="log")
        else:
            st.caption("Pipeline logs appear here after you run a step.")

    def tab_scoreboard() -> None:
        if not agg:
            st.caption("No aggregate scores yet.")
            return

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Mean score", f"{agg['mean_total'] * 10:.1f} / 10")
        m2.metric("Pass rate", f"{agg['pass_rate']:.0%}")
        m3.metric("Passing", f"{agg['n_passing']} / {agg['n_cases']}")
        m4.metric("Emails", len(emails))

        failure_tags = _compute_failure_tags(scores)
        if failure_tags:
            st.plotly_chart(
                charts.failure_tag_chart(failure_tags),
                width="stretch",
                key="step1_failure_tag_chart",
            )

        rows = [
            {"Scorer": k, "Score /10": round(v * 10, 2)}
            for k, v in agg.get("mean_per_scorer", {}).items()
        ]
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)

        if emails:
            st.markdown("**Sample emails — lowest scores first**")
            worst_first = sorted(
                emails,
                key=lambda e: scores.get(e["case_id"], {}).get("mean_score", 1.0),
            )
            for email in worst_first[:3]:
                sc = scores.get(email["case_id"], {})
                cust = customers.get(email.get("customer_id", ""), {})
                prod = products.get(email.get("product_id", ""), {})
                failure_tags_list = [
                    ev["name"]
                    for ev in sc.get("evaluations", [])
                    if ev.get("value", 1.0) < 1.0
                ]
                ui.email_card(
                    company=cust.get("company_name", email.get("customer_id", "")),
                    product=prod.get("name", email.get("product_id", "")),
                    subject=email.get("subject", ""),
                    body=email.get("body", ""),
                    score=sc.get("mean_score"),
                    failure_tags=failure_tags_list,
                )

    def tab_langfuse() -> None:
        trace_metadata = None
        trace_path = _OUTPUTS / _RUN_ID / "trace_metadata.json"
        if trace_path.exists():
            try:
                trace_metadata = json.loads(trace_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        embeds.render_langfuse_panel(
            trace_metadata if isinstance(trace_metadata, list) else None,
            title="Langfuse — Run 1",
        )

    with ui.story_section("Observe & results"):
        embeds.render_horizontal_tabs(
            ["Run logs", "Scoreboard", "Langfuse"],
            [tab_logs, tab_scoreboard, tab_langfuse],
        )
