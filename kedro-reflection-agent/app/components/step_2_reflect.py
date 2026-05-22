"""Step 2 — Reflect on failures and approve improvements.

Component tree:
    render(state)
    ├── _reflect_action(state)          # Run Reflection button + live log
    ├── _summary_panel(md)              # narrative cards
    ├── _prompt_diff(current, proposed) # word-level diff
    ├── _skill_diff(current, proposed)  # word-level diff
    ├── _eval_cases_preview(cases)      # proposed regression cases table
    └── _approve_action(state)          # Approve & Apply button + live log
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from app import runner
from app import state as demo_state
from app import ui_components as ui

_RUN_ID = "run_1"
_REFLECTION_ID = "refl_1"
_DATA = Path("data")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

@st.cache_data
def _load_current_prompt() -> list[dict]:
    p = _DATA / "campaign" / "prompts" / "system_prompt.json"
    return json.loads(p.read_text()) if p.exists() else []


@st.cache_data
def _load_current_skill() -> str:
    p = _DATA / "campaign" / "skills" / "b2b_email_style.md"
    return p.read_text() if p.exists() else ""


@st.cache_data
def _load_summary_md(reflection_id: str) -> str:
    p = _DATA / "outputs" / "reflections" / reflection_id / "summary.md"
    return p.read_text() if p.exists() else ""


@st.cache_data
def _load_proposed_prompt(reflection_id: str) -> list[dict]:
    p = _DATA / "outputs" / "reflections" / reflection_id / "proposed_prompt.json"
    return json.loads(p.read_text()) if p.exists() else []


@st.cache_data
def _load_proposed_skill(reflection_id: str) -> str:
    p = _DATA / "outputs" / "reflections" / reflection_id / "proposed_skill.md"
    return p.read_text() if p.exists() else ""


@st.cache_data
def _load_proposed_eval_cases(reflection_id: str) -> list[dict]:
    p = _DATA / "outputs" / "reflections" / reflection_id / "proposed_eval_cases.json"
    return json.loads(p.read_text()) if p.exists() else []


@st.cache_data
def _load_aggregate(run_id: str) -> dict:
    p = _DATA / "outputs" / "runs" / run_id / "aggregate_scores.json"
    return json.loads(p.read_text()) if p.exists() else {}


# ---------------------------------------------------------------------------
# Leaf components
# ---------------------------------------------------------------------------

def _summary_panel(md: str, agg: dict) -> None:
    import re
    issues = re.findall(r"^### (.+)$", md, re.MULTILINE)
    changes = re.findall(r"^\- \*\*(.+?)\*\*: (.+)$", md, re.MULTILINE)
    reasons = re.findall(r"^- (?!\*\*)(.+)$", md, re.MULTILINE)

    cols = st.columns(3)
    with cols[0]:
        ui.card(
            "Issues found",
            "\n".join(f"• {i}" for i in issues[:4]) or md[:200],
            border_left_color="#CBD5E0",
        )
    with cols[1]:
        ui.card(
            "Planned fixes",
            "\n".join(f"• {t}: {c}" for t, c in changes[:4]),
            border_left_color="#1A1A1A",
        )
    with cols[2]:
        dims = agg.get("mean_per_scorer", {})
        ui.card(
            "Current scores",
            "\n".join(
                f"• {k}: {v * 10:.1f}/10" for k, v in dims.items()
            ),
            border_left_color="#0251AA",
        )

    with st.expander("Full narrative", expanded=False):
        st.markdown(md)


def _prompt_diff(current: list[dict], proposed: list[dict]) -> None:
    cur_text = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in current)
    prop_text = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in proposed)
    ui.text_diff_card("Current prompt (v1)", "Proposed prompt (v2)", cur_text, prop_text)


def _skill_diff(current: str, proposed: str) -> None:
    ui.text_diff_card("Current skill file", "Proposed skill file", current, proposed)


def _eval_cases_preview(cases: list[dict]) -> None:
    if not cases:
        st.info("No new eval cases proposed.")
        return
    rows = []
    for case in cases:
        inp = case.get("input", {})
        rubric = (case.get("expected_output") or {}).get("rubric", {})
        rows.append({
            "ID": case.get("id", ""),
            "Customer": inp.get("customer_id", ""),
            "Product": inp.get("product_id", ""),
            "CTA": rubric.get("expected_cta", ""),
            "Tone": rubric.get("expected_tone", ""),
            "Notes": rubric.get("notes", "")[:80] + "…" if len(rubric.get("notes", "")) > 80 else rubric.get("notes", ""),
        })
    st.dataframe(rows, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Action components
# ---------------------------------------------------------------------------

def _reflect_action(current_state: str) -> None:
    disabled = not demo_state.reached("run_1_done") or demo_state.reached("reflected")
    st.code(
        f'kedro run --pipelines reflection --params "run_id={_RUN_ID},reflection_id={_REFLECTION_ID}"',
        language="bash",
    )
    if st.button("Run Reflection", disabled=disabled, type="primary", key="btn_reflect"):
        log_lines: list[str] = st.session_state.setdefault("step2_logs", [])
        log_lines.clear()
        log_target = ui.pipeline_log_slot()
        with st.spinner("Running reflection meta-agent…"):
            ok, _ = runner.run_reflection(
                _RUN_ID, _REFLECTION_ID,
                on_log=lambda line: (
                    log_lines.append(line),
                    ui.update_pipeline_log(log_target, log_lines),
                ),
            )
        if ok:
            st.cache_data.clear()
            demo_state.set_state("reflected")
            st.rerun()
        else:
            st.error("Reflection failed — see log above.")

    if st.session_state.get("step2_logs"):
        with st.expander("Pipeline log", expanded=False):
            st.code("".join(st.session_state["step2_logs"][-150:]), language="log")


def _approve_action(current_state: str) -> None:
    disabled = not demo_state.reached("reflected") or demo_state.reached("applied")
    st.code(
        f'kedro run --pipelines apply --params "reflection_id={_REFLECTION_ID}"',
        language="bash",
    )
    if st.button("Approve & Apply", disabled=disabled, type="primary", key="btn_apply"):
        log_lines: list[str] = st.session_state.setdefault("step2_apply_logs", [])
        log_lines.clear()
        log_target = ui.pipeline_log_slot()
        with st.spinner("Applying to live prompt, skill, and eval dataset…"):
            ok, _ = runner.run_apply(
                _REFLECTION_ID,
                on_log=lambda line: (
                    log_lines.append(line),
                    ui.update_pipeline_log(log_target, log_lines),
                ),
            )
        if ok:
            st.cache_data.clear()
            demo_state.set_state("applied")
            st.success("Prompt v2 and regression eval cases are now active.")
            st.rerun()
        else:
            st.error("Apply failed — see log above.")

    if st.session_state.get("step2_apply_logs"):
        with st.expander("Apply log", expanded=False):
            st.code("".join(st.session_state["step2_apply_logs"][-150:]), language="log")


# ---------------------------------------------------------------------------
# Step root
# ---------------------------------------------------------------------------

def render(current_state: str) -> None:
    reflected = demo_state.reached("reflected")
    applied = demo_state.reached("applied")
    ui.step_heading(
        "STEP 2 — Reflect & Approve",
        done=reflected,
        muted=not demo_state.reached("run_1_done"),
    )

    if not demo_state.reached("run_1_done"):
        st.caption("Complete Step 1 first.")
        return

    with ui.story_section("Run"):
        _reflect_action(current_state)

    if not reflected:
        return

    agg = _load_aggregate(_RUN_ID)

    with ui.story_section("Proposal summary"):
        _summary_panel(_load_summary_md(_REFLECTION_ID), agg)

    with ui.story_section("Prompt diff  (v1 → proposed v2)"):
        _prompt_diff(_load_current_prompt(), _load_proposed_prompt(_REFLECTION_ID))

    with ui.story_section("Skill diff"):
        with st.expander("Show skill diff", expanded=False):
            _skill_diff(_load_current_skill(), _load_proposed_skill(_REFLECTION_ID))

    with ui.story_section("New regression eval cases"):
        with st.expander("Show proposed cases", expanded=False):
            _eval_cases_preview(_load_proposed_eval_cases(_REFLECTION_ID))

    st.divider()
    with ui.story_section("Approve"):
        if applied:
            st.success("Changes applied — prompt v2 is now live. Run Step 3 to measure improvement.")
        else:
            _approve_action(current_state)
