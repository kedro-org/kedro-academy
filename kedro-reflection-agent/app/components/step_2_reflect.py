"""Step 2 — Reflect on failures and approve improvements."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app import runner
from app import ui_components as ui
from app import embeds
from app.state import DemoState, save_demo_state, transition, DEFAULT_STATE_PATH

_RUN_ID = "run_1"
_REFLECTION_ID = "refl_1"
_DATA = Path("data")
_OUTPUTS = _DATA / "outputs"
_REFL_DIR = _OUTPUTS / "reflections" / _REFLECTION_ID


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

@st.cache_data
def _load_summary_md(reflection_id: str) -> str:
    p = _OUTPUTS / "reflections" / reflection_id / "summary.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


@st.cache_data
def _load_current_prompt() -> list[dict]:
    p = _DATA / "campaign" / "prompts" / "system_prompt.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@st.cache_data
def _load_current_skill() -> str:
    p = _DATA / "campaign" / "skills" / "b2b_email_style.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


@st.cache_data
def _load_proposed_prompt(reflection_id: str) -> list[dict]:
    p = _OUTPUTS / "reflections" / reflection_id / "proposed_prompt.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@st.cache_data
def _load_proposed_skill(reflection_id: str) -> str:
    p = _OUTPUTS / "reflections" / reflection_id / "proposed_skill.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


@st.cache_data
def _load_proposed_eval_cases(reflection_id: str) -> list[dict]:
    p = _OUTPUTS / "reflections" / reflection_id / "proposed_eval_cases.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@st.cache_data
def _load_aggregate(run_id: str) -> dict:
    p = _OUTPUTS / "runs" / run_id / "aggregate_scores.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ---------------------------------------------------------------------------
# Step root
# ---------------------------------------------------------------------------

def render(demo: DemoState) -> None:
    reflected = demo.state in ("reflected", "applied", "run_2_done")
    applied = demo.state in ("applied", "run_2_done")

    ui.step_heading(
        "STEP 2 — Reflect & Approve",
        done=reflected,
        muted=demo.state == "idle",
    )

    with ui.story_section("Pipeline"):
        embeds.render_kedro_viz_pipeline_picker(
            project_root=str(runner.PROJECT_ROOT),
            pipelines=embeds.STEP2_PIPELINES,
            default_pipeline_id="reflection",
            height=480,
            session_key="viz_pipeline_step2",
        )

    with ui.story_section("Run"):
        st.code(
            f'kedro run --pipelines reflection --params "run_id={_RUN_ID},reflection_id={_REFLECTION_ID}"\n'
            f'kedro run --pipelines apply --params "reflection_id={_REFLECTION_ID}"',
            language="bash",
        )
        r1, _gap, r2 = st.columns([1, 0.1, 1])
        with r1:
            reflect_clicked = st.button(
                "Run Reflection",
                disabled=not demo.can_run_reflection(),
                type="primary",
                key="step2_reflect",
            )
        with r2:
            apply_clicked = st.button(
                "Approve & Apply",
                disabled=not demo.can_apply(),
                key="step2_apply",
            )

        log_target = ui.pipeline_log_slot()

        if reflect_clicked:
            log_lines: list[str] = []
            st.session_state["step2_logs"] = log_lines

            def _log(line: str) -> None:
                log_lines.append(line)
                ui.update_pipeline_log(log_target, log_lines)

            with st.spinner("Running reflection meta-agent…"):
                ok, _ = runner.run_reflection(_RUN_ID, _REFLECTION_ID, on_log=_log)

            if ok:
                st.cache_data.clear()
                new_demo = transition(demo, "reflected", reflection_id=_REFLECTION_ID)
                save_demo_state(new_demo, DEFAULT_STATE_PATH)
                st.rerun()
            else:
                st.error("Reflection failed — see log above.")

        if apply_clicked:
            log_lines_apply: list[str] = st.session_state.setdefault("step2_apply_logs", [])

            def _log_apply(line: str) -> None:
                log_lines_apply.append(line)
                ui.update_pipeline_log(log_target, log_lines_apply)

            with st.spinner("Applying to live prompt, skill, and eval dataset…"):
                ok, _ = runner.run_apply(_REFLECTION_ID, on_log=_log_apply)

            if ok:
                st.cache_data.clear()
                new_demo = transition(demo, "applied", applied_id=_REFLECTION_ID)
                save_demo_state(new_demo, DEFAULT_STATE_PATH)
                st.success("Prompt v2 and regression eval cases are now active.")
                st.rerun()
            else:
                st.error("Apply failed — see log above.")

    if demo.state == "idle":
        st.caption("Finish Step 1 first.")
        return
    if not (_REFL_DIR / "summary.md").exists():
        st.caption("Run reflection to unlock the tabs below.")
        return

    agg = _load_aggregate(_RUN_ID)
    dims = agg.get("mean_per_scorer", {})

    def tab_logs() -> None:
        lines = st.session_state.get("step2_logs") or st.session_state.get("step2_apply_logs") or []
        if lines:
            st.code("".join(lines[-200:]), language="log")
        else:
            st.caption("Pipeline logs appear here after you run a step.")

    def tab_proposal() -> None:
        summary_md = _load_summary_md(_REFLECTION_ID)
        current_prompt = _load_current_prompt()
        proposed_prompt = _load_proposed_prompt(_REFLECTION_ID)
        current_skill = _load_current_skill()
        proposed_skill = _load_proposed_skill(_REFLECTION_ID)
        new_cases = _load_proposed_eval_cases(_REFLECTION_ID)

        import re
        issues = re.findall(r"^### (.+)$", summary_md, re.MULTILINE)
        changes = re.findall(r"^\- \*\*(.+?)\*\*: (.+)$", summary_md, re.MULTILINE)

        c1, c2, c3 = st.columns(3)
        with c1:
            ui.card(
                "Issues found",
                "\n".join(f"• {i}" for i in issues[:4]) or summary_md[:200],
                border_left_color="#CBD5E0",
            )
        with c2:
            ui.card(
                "Planned fixes",
                "\n".join(f"• {t}: {c}" for t, c in changes[:4]),
                border_left_color="#1A1A1A",
            )
        with c3:
            ui.card(
                "Current scores",
                "\n".join(f"• {k}: {v * 10:.1f}/10" for k, v in dims.items()),
                border_left_color="#0251AA",
            )

        with st.expander("Full narrative", expanded=False):
            st.markdown(summary_md)

        st.markdown("**Prompt diff (v1 → proposed v2)**")
        cur_text = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in current_prompt)
        prop_text = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in proposed_prompt)
        if cur_text or prop_text:
            ui.text_diff_card("Current prompt (v1)", "Proposed prompt (v2)", cur_text, prop_text)

        with st.expander("Skill diff", expanded=False):
            if current_skill or proposed_skill:
                ui.text_diff_card("Current skill file", "Proposed skill file", current_skill, proposed_skill)
            else:
                st.caption("No skill files found.")

        with st.expander("New regression eval cases", expanded=False):
            if not new_cases:
                st.caption("No new eval cases proposed.")
            else:
                rows = []
                for case in new_cases:
                    inp = case.get("input", case)
                    rubric = (case.get("expected_output") or case.get("rubric") or {})
                    if isinstance(rubric, dict) and "rubric" in rubric:
                        rubric = rubric["rubric"]
                    rows.append({
                        "ID": case.get("case_id", case.get("id", "")),
                        "Customer": inp.get("customer_id", ""),
                        "Product": inp.get("product_id", ""),
                        "CTA": rubric.get("expected_cta", ""),
                        "Tone": rubric.get("expected_tone", ""),
                    })
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        if applied:
            st.caption("Changes applied locally. Run Step 3 to measure improvement.")

    def tab_langfuse() -> None:
        embeds.render_langfuse_panel(title="Langfuse — project overview")

    with ui.story_section("Observe & results"):
        embeds.render_horizontal_tabs(
            ["Run logs", "Proposal", "Langfuse"],
            [tab_logs, tab_proposal, tab_langfuse],
        )
