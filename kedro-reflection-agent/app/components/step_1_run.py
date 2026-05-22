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
def _load_scores_list(run_id: str) -> list[dict]:
    p = _OUTPUTS / run_id / "per_case_scores.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


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

    # Filter scores to only cases that have a local email file — the Langfuse
    # experiment may score the full dataset including historic/other-run cases.
    _local_email_ids = {e["case_id"] for e in _load_emails(_RUN_ID)} if done else set()
    scores_list = [
        s for s in (_load_scores_list(_RUN_ID) if done else [])
        if s["case_id"] in _local_email_ids
    ]

    with ui.story_section("Run"):
        st.code(
            'kedro run --pipelines campaign --params "run_id=run_1"\n'
            'kedro run --pipelines evaluation --params "run_id=run_1"',
            language="bash",
        )
        c1, _, c3, c4 = st.columns([2, 0.1, 1, 1])
        with c1:
            run_clicked = st.button(
                "Run Generate & Evaluate",
                disabled=not demo.can_run_agent_step1(),
                type="primary",
                key="step1_run",
            )
        with c3:
            if scores_list:
                _m = sum(s.get("mean_score", 0.0) for s in scores_list) / len(scores_list)
                st.metric("Mean score", f"{_m * 10:.1f}/10")
            else:
                st.metric("Mean score", "—")
        with c4:
            if scores_list:
                _p = sum(1 for s in scores_list if s.get("passing", False))
                st.metric("Passing", f"{_p} / {len(scores_list)}")
            else:
                st.metric("Passing", "—")

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
    scores = {k: v for k, v in _load_scores_by_case(_RUN_ID).items() if k in _local_email_ids}
    customers = _load_customers()
    products = _load_products()

    def tab_logs() -> None:
        lines = st.session_state.get("step1_logs") or []
        if lines:
            st.code("".join(lines[-200:]), language="log")
        else:
            st.caption("Pipeline logs appear here after you run a step.")

    def tab_scoreboard() -> None:
        if not scores_list:
            st.caption("No scores yet.")
            return

        local_n = len(scores_list)
        local_passing = sum(1 for s in scores_list if s.get("passing", False))
        local_pass_rate = local_passing / local_n if local_n else 0.0
        local_mean = (
            sum(s.get("mean_score", 0.0) for s in scores_list) / local_n
            if local_n else 0.0
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Mean score", f"{local_mean * 10:.1f} / 10")
        m2.metric("Pass rate", f"{local_pass_rate:.0%}")
        m3.metric("Passing", f"{local_passing} / {local_n}")
        m4.metric("Emails generated", local_n)

        failure_tags = _compute_failure_tags(scores)
        if failure_tags:
            st.plotly_chart(
                charts.failure_tag_chart(failure_tags),
                width="stretch",
                key="step1_failure_tag_chart",
            )

        # Compute per-scorer means from local scores only
        scorer_vals: dict[str, list[float]] = {}
        for sc in scores_list:
            for ev in sc.get("evaluations", []):
                scorer_vals.setdefault(ev["name"], []).append(ev.get("value", 0.0))
        local_per_scorer = {k: sum(v) / len(v) for k, v in scorer_vals.items()}
        rows = [
            {"Scorer": k, "Score /10": round(v * 10, 2)}
            for k, v in local_per_scorer.items()
        ]
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)

        if emails:
            st.markdown(f"**Generated emails ({len(emails)})**")
            for email in emails:
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
