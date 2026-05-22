"""Step 1 — Generate emails and evaluate them.

Component tree:
    render(state)
    ├── _run_action(state)            # primary button + live log streaming
    ├── _score_panel(agg)             # metrics + per-scorer breakdown
    └── _emails_panel(emails, scores, customers, products)
        └── email_card() per email
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from app import runner
from app import state as demo_state
from app import ui_components as ui

_RUN_ID = "run_1"
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
    if not p.exists():
        return {}
    return {c["customer_id"]: c for c in json.loads(p.read_text())}


@st.cache_data
def _load_products() -> dict[str, dict]:
    p = _DATA / "seed" / "products.json"
    if not p.exists():
        return {}
    return {p["product_id"]: p for p in json.loads(p.read_text())}


# ---------------------------------------------------------------------------
# Leaf components
# ---------------------------------------------------------------------------

def _score_panel(agg: dict) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Pass rate", f"{agg['pass_rate']:.0%}",
              help=f"Threshold: {agg['passing_threshold']}")
    c2.metric("Mean score", f"{agg['mean_total'] * 10:.2f} / 10")
    c3.metric("Passing cases", f"{agg['n_passing']} / {agg['n_cases']}")

    with ui.story_section("Per-scorer breakdown"):
        rows = [
            {"Scorer": k, "Score": round(v, 3), "Score /10": round(v * 10, 2)}
            for k, v in agg["mean_per_scorer"].items()
        ]
        st.dataframe(rows, width="stretch", hide_index=True)


def _emails_panel(
    emails: list[dict],
    scores: dict[str, dict],
    customers: dict[str, dict],
    products: dict[str, dict],
) -> None:
    if not emails:
        st.info("No emails generated yet.")
        return

    worst_first = sorted(
        emails,
        key=lambda e: scores.get(e["case_id"], {}).get("mean_score", 1.0),
    )
    for email in worst_first:
        sc = scores.get(email["case_id"], {})
        cust = customers.get(email["customer_id"], {})
        prod = products.get(email["product_id"], {})
        failure_tags = [
            e["name"]
            for e in sc.get("evaluations", [])
            if e["value"] < 1.0 and not e["name"].startswith("length")
        ]
        ui.email_card(
            company=cust.get("company_name", email["customer_id"]),
            product=prod.get("name", email["product_id"]),
            subject=email["subject"],
            body=email["body"],
            score=sc.get("mean_score"),
            failure_tags=failure_tags,
        )


# ---------------------------------------------------------------------------
# Action component — live log streaming
# ---------------------------------------------------------------------------

def _run_action(current_state: str) -> None:
    already_done = demo_state.reached("run_1_done")
    st.code(
        'kedro run --pipelines campaign --params "run_id=run_1"\n'
        'kedro run --pipelines evaluation --params "run_id=run_1"',
        language="bash",
    )
    if st.button(
        "Run Generate & Evaluate",
        disabled=already_done,
        type="primary",
        key="btn_run_1",
    ):
        log_lines: list[str] = st.session_state.setdefault("step1_logs", [])
        log_lines.clear()
        log_target = ui.pipeline_log_slot()
        with st.spinner("Running campaign and evaluation for run_1…"):
            ok, _ = runner.run_campaign(
                _RUN_ID,
                on_log=lambda line: (
                    log_lines.append(line),
                    ui.update_pipeline_log(log_target, log_lines),
                ),
            )
        if ok:
            st.cache_data.clear()
            demo_state.set_state("run_1_done")
            st.rerun()
        else:
            st.error("Pipeline failed — see log above.")

    if st.session_state.get("step1_logs"):
        with st.expander("Pipeline log", expanded=False):
            st.code(
                "".join(st.session_state["step1_logs"][-150:]),
                language="log",
            )


# ---------------------------------------------------------------------------
# Step root
# ---------------------------------------------------------------------------

def render(current_state: str) -> None:
    done = demo_state.reached("run_1_done")
    ui.step_heading("STEP 1 — Generate & Evaluate", done=done)

    with ui.story_section("Run"):
        _run_action(current_state)

    if not done:
        return

    agg = _load_aggregate(_RUN_ID)
    if agg:
        with ui.story_section("Scores"):
            _score_panel(agg)

    emails = _load_emails(_RUN_ID)
    if emails:
        with ui.story_section("Emails — worst scoring first"):
            _emails_panel(
                emails,
                _load_scores_by_case(_RUN_ID),
                _load_customers(),
                _load_products(),
            )
