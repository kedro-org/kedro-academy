"""Step 3 — Re-run campaign with improved prompt/skill and compare.

Component tree:
    render(state)
    ├── _rerun_action(state)               # Re-run button + live log
    ├── _score_headline(run1, run2)        # large before/after cards
    ├── _scorer_table(run1, run2)          # per-scorer delta table
    └── _email_diff_panel(emails1, emails2, scores1, scores2)
        └── email_diff_cards() per worst case
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from app import runner
from app import state as demo_state
from app import ui_components as ui

_RUN_ID_1 = "run_1"
_RUN_ID_2 = "run_2"
_DATA = Path("data")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

@st.cache_data
def _load_aggregate(run_id: str) -> dict | None:
    p = _DATA / "outputs" / "runs" / run_id / "aggregate_scores.json"
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_data
def _load_emails(run_id: str) -> list[dict]:
    d = _DATA / "outputs" / "runs" / run_id / "emails"
    if not d.exists():
        return []
    return [json.loads(f.read_text()) for f in sorted(d.glob("*.json"))]


@st.cache_data
def _load_scores_by_case(run_id: str) -> dict[str, dict]:
    p = _DATA / "outputs" / "runs" / run_id / "per_case_scores.json"
    if not p.exists():
        return {}
    return {s["case_id"]: s for s in json.loads(p.read_text())}


@st.cache_data
def _load_customers() -> dict[str, dict]:
    p = _DATA / "seed" / "customers.json"
    return {c["customer_id"]: c for c in json.loads(p.read_text())} if p.exists() else {}


@st.cache_data
def _load_products() -> dict[str, dict]:
    p = _DATA / "seed" / "products.json"
    return {p["product_id"]: p for p in json.loads(p.read_text())} if p.exists() else {}


# ---------------------------------------------------------------------------
# Leaf components
# ---------------------------------------------------------------------------

def _scorer_table(run1: dict, run2: dict) -> None:
    rows = []
    for scorer, before in run1["mean_per_scorer"].items():
        after = run2["mean_per_scorer"].get(scorer, 0.0)
        delta = after - before
        rows.append({
            "Scorer": scorer,
            "Before (run_1)": f"{before * 10:.2f}",
            "After (run_2)": f"{after * 10:.2f}",
            "Δ": f"{delta * 10:+.2f}",
        })
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
    st.dataframe(rows, width="stretch", hide_index=True)


def _email_diff_panel(
    emails_1: list[dict],
    emails_2: list[dict],
    scores_1: dict[str, dict],
    scores_2: dict[str, dict],
    customers: dict[str, dict],
    products: dict[str, dict],
) -> None:
    by_case_1 = {e["case_id"]: e for e in emails_1}
    by_case_2 = {e["case_id"]: e for e in emails_2}
    worst_cases = sorted(
        by_case_1.keys(),
        key=lambda cid: scores_1.get(cid, {}).get("mean_score", 1.0),
    )[:5]

    for case_id in worst_cases:
        e1 = by_case_1.get(case_id, {})
        e2 = by_case_2.get(case_id, {})
        sc1 = scores_1.get(case_id, {})
        sc2 = scores_2.get(case_id, {})
        cust = customers.get(e1.get("customer_id", ""), {})
        prod = products.get(e1.get("product_id", ""), {})
        failure_tags = [
            ev["name"]
            for ev in sc1.get("evaluations", [])
            if ev["value"] < 1.0 and not ev["name"].startswith("length")
        ]
        ui.email_diff_cards(
            company=cust.get("company_name", e1.get("customer_id", case_id)),
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


# ---------------------------------------------------------------------------
# Action component
# ---------------------------------------------------------------------------

def _rerun_action(current_state: str) -> None:
    disabled = not demo_state.reached("applied") or demo_state.reached("run_2_done")
    st.code(
        'kedro run --pipelines campaign --params "run_id=run_2"\n'
        'kedro run --pipelines evaluation --params "run_id=run_2"',
        language="bash",
    )
    if st.button(
        "Re-run Generate & Evaluate",
        disabled=disabled,
        type="primary",
        key="btn_run_2",
    ):
        log_lines: list[str] = st.session_state.setdefault("step3_logs", [])
        log_lines.clear()
        log_target = ui.pipeline_log_slot()
        with st.spinner("Running campaign and evaluation for run_2…"):
            ok, _ = runner.run_campaign(
                _RUN_ID_2,
                on_log=lambda line: (
                    log_lines.append(line),
                    ui.update_pipeline_log(log_target, log_lines),
                ),
            )
        if ok:
            st.cache_data.clear()
            demo_state.set_state("run_2_done")
            st.rerun()
        else:
            st.error("Pipeline failed — see log above.")

    if st.session_state.get("step3_logs"):
        with st.expander("Pipeline log", expanded=False):
            st.code("".join(st.session_state["step3_logs"][-150:]), language="log")


# ---------------------------------------------------------------------------
# Step root
# ---------------------------------------------------------------------------

def render(current_state: str) -> None:
    done = demo_state.reached("run_2_done")
    ui.step_heading(
        "STEP 3 — Re-run & Compare",
        done=done,
        muted=not demo_state.reached("applied"),
    )

    if not demo_state.reached("applied"):
        st.caption("Approve and apply in Step 2 before re-running.")
        return

    with ui.story_section("Run"):
        _rerun_action(current_state)

    if not done:
        return

    run1 = _load_aggregate(_RUN_ID_1)
    run2 = _load_aggregate(_RUN_ID_2)

    if run1 and run2:
        with ui.story_section("Score comparison"):
            ui.score_headline(run1["mean_total"], run2["mean_total"])
            _scorer_table(run1, run2)

    emails_1 = _load_emails(_RUN_ID_1)
    emails_2 = _load_emails(_RUN_ID_2)
    if emails_1 or emails_2:
        with ui.story_section("Email before/after — word-level diff (worst Run 1 cases)"):
            _email_diff_panel(
                emails_1, emails_2,
                _load_scores_by_case(_RUN_ID_1),
                _load_scores_by_case(_RUN_ID_2),
                _load_customers(),
                _load_products(),
            )
