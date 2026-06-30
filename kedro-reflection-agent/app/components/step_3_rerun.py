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
def _load_emails(run_id: str) -> list[dict]:
    d = _OUTPUTS / run_id / "emails"
    if not d.exists():
        return []
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("*.json"))]


@st.cache_data
def _load_scores_list(run_id: str) -> list[dict]:
    p = _OUTPUTS / run_id / "per_case_scores.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@st.cache_data
def _load_customers() -> dict[str, dict]:
    p = _DATA / "seed" / "customers.json"
    return {c["customer_id"]: c for c in json.loads(p.read_text(encoding="utf-8"))} if p.exists() else {}


@st.cache_data
def _load_products() -> dict[str, dict]:
    p = _DATA / "seed" / "products.json"
    return {prod["product_id"]: prod for prod in json.loads(p.read_text(encoding="utf-8"))} if p.exists() else {}




def _local_stats(scores_list: list[dict]) -> dict:
    """Compute headline stats from a locally-filtered scores list."""
    n = len(scores_list)
    if n == 0:
        return {"mean": 0.0, "pass_rate": 0.0, "n_passing": 0, "n": 0, "per_scorer": {}}
    passing = sum(1 for s in scores_list if s.get("passing", False))
    mean = sum(s.get("mean_score", 0.0) for s in scores_list) / n
    scorer_vals: dict[str, list[float]] = {}
    for sc in scores_list:
        for ev in sc.get("evaluations", []):
            scorer_vals.setdefault(ev["name"], []).append(ev.get("value", 0.0))
    per_scorer = {k: sum(v) / len(v) for k, v in scorer_vals.items()}
    return {"mean": mean, "pass_rate": passing / n, "n_passing": passing, "n": n, "per_scorer": per_scorer}


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

    # Load emails for both runs and derive local case ID sets
    emails1_list = _load_emails(_RUN_ID_1)
    emails2_list = _load_emails(_RUN_ID_2)
    email_ids_1 = {e["case_id"] for e in emails1_list}
    email_ids_2 = {e["case_id"] for e in emails2_list}
    # Only compare cases present in BOTH runs
    shared_ids = email_ids_1 & email_ids_2

    emails1 = {e["case_id"]: e for e in emails1_list}
    emails2 = {e["case_id"]: e for e in emails2_list}

    # Filter per-case scores to locally generated emails only
    scores1 = {
        s["case_id"]: s
        for s in _load_scores_list(_RUN_ID_1)
        if s["case_id"] in email_ids_1
    }
    scores2 = {
        s["case_id"]: s
        for s in _load_scores_list(_RUN_ID_2)
        if s["case_id"] in email_ids_2
    }

    # Compute all stats locally
    stats1 = _local_stats([s for s in scores1.values() if s["case_id"] in shared_ids])
    stats2 = _local_stats([s for s in scores2.values() if s["case_id"] in shared_ids])

    customers = _load_customers()
    products = _load_products()

    def tab_logs() -> None:
        lines = st.session_state.get("step3_logs") or []
        if lines:
            st.code("".join(lines[-200:]), language="log")
        else:
            st.caption("Pipeline logs appear here after you run a step.")

    def tab_compare() -> None:
        if not shared_ids:
            st.caption("No matching cases found across both runs.")
            return

        ui.score_headline(stats1["mean"], stats2["mean"])

        if stats1["per_scorer"] and stats2["per_scorer"]:
            st.plotly_chart(
                charts.dimension_bar_chart(stats1["per_scorer"], stats2["per_scorer"]),
                width="stretch",
                key="step3_dimension_bar_chart",
            )

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Pass rate",
            f"{stats2['pass_rate']:.0%}",
            delta=f"{(stats2['pass_rate'] - stats1['pass_rate']):+.0%}",
        )
        c2.metric(
            "Mean score",
            f"{stats2['mean'] * 10:.2f} / 10",
            delta=f"{(stats2['mean'] - stats1['mean']) * 10:+.2f}",
        )
        c3.metric(
            "Passing cases",
            f"{stats2['n_passing']} / {stats2['n']}",
            delta=stats2["n_passing"] - stats1["n_passing"],
        )

        with st.expander("Per-case score deltas", expanded=True):
            rows = []
            for cid in shared_ids:
                sc1 = scores1.get(cid, {})
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
            worst = sorted(
                [s for s in scores1.values() if s["case_id"] in shared_ids],
                key=lambda s: s.get("mean_score", 1.0),
            )[:3]
            for sc1 in worst:
                cid = sc1["case_id"]
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
        embeds.render_langfuse_panel(title="Langfuse", key_prefix="step3_lf")

    with ui.story_section("Observe & results"):
        embeds.render_horizontal_tabs(
            ["Run logs", "Compare", "Langfuse"],
            [tab_logs, tab_compare, tab_langfuse],
        )
