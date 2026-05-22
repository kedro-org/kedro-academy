"""Step 2 — Reflect on failures and approve improvements."""

from __future__ import annotations

import json
import re
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
def _load_current_eval_cases() -> list[dict]:
    p = _DATA / "evaluation" / "eval_cases.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@st.cache_data
def _load_run_emails(run_id: str) -> list[dict]:
    d = _OUTPUTS / "runs" / run_id / "emails"
    if not d.exists():
        return []
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("*.json"))]


@st.cache_data
def _load_run_scores_list(run_id: str) -> list[dict]:
    p = _OUTPUTS / "runs" / run_id / "per_case_scores.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


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

    # Compute per-scorer means from local email files only (same approach as step 1)
    _run1_email_ids = {e["case_id"] for e in _load_run_emails(_RUN_ID)}
    _run1_scores = [
        s for s in _load_run_scores_list(_RUN_ID)
        if s["case_id"] in _run1_email_ids
    ]
    _scorer_vals: dict[str, list[float]] = {}
    for _sc in _run1_scores:
        for _ev in _sc.get("evaluations", []):
            _scorer_vals.setdefault(_ev["name"], []).append(_ev.get("value", 0.0))
    local_per_scorer = {k: sum(v) / len(v) for k, v in _scorer_vals.items()}

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
        current_cases = _load_current_eval_cases()

        issues = re.findall(r"^### (.+)$", summary_md, re.MULTILINE)
        changes = re.findall(r"^\- \*\*(.+?)\*\*: (.+)$", summary_md, re.MULTILINE)

        # 1. Cards: Current scores | Issues found | Planned fixes
        c1, c2, c3 = st.columns(3)
        with c1:
            scores_text = (
                "\n".join(f"• {k}: {v * 10:.1f}/10" for k, v in local_per_scorer.items())
                or "No local scores available."
            )
            ui.card("Current scores", scores_text, border_left_color="#0251AA")
        with c2:
            issues_text = "\n".join(f"• {i[:80]}" for i in issues[:4])
            ui.card(
                "Issues found",
                issues_text or summary_md[:200],
                border_left_color="#CBD5E0",
            )
        with c3:
            fixes_text = "\n".join(f"• {t}: {c[:60]}" for t, c in changes[:4])
            ui.card(
                "Planned fixes",
                fixes_text or "—",
                border_left_color="#1A1A1A",
            )

        # 2. Prompt diff
        st.markdown("**Prompt diff (v1 → proposed v2)**")
        if not proposed_prompt:
            st.caption("No proposed prompt from this reflection run — the skill file was updated instead.")
        else:
            cur_text = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in current_prompt)
            prop_text = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in proposed_prompt)
            ui.text_diff_card("Current prompt (v1)", "Proposed prompt (v2)", cur_text, prop_text)

        # 3. Skill diff
        with st.expander("Skill diff", expanded=True):
            if current_skill or proposed_skill:
                ui.text_diff_card("Current skill file", "Proposed skill file", current_skill, proposed_skill)
            else:
                st.caption("No skill files found.")

        # 4. Evals diff — proposed additions to the eval suite
        with st.expander("Evals diff", expanded=False):
            if not new_cases:
                st.caption("No new eval cases proposed.")
            else:
                current_ids = {c.get("id", c.get("case_id", "")) for c in current_cases}
                n_new = sum(1 for c in new_cases if c.get("id", c.get("case_id", "")) not in current_ids)
                n_mod = len(new_cases) - n_new
                st.info(
                    f"The reflection agent proposed {n_new} new eval case(s) to add to the "
                    f"evaluation suite, targeting the failure patterns it identified. "
                    f"{len(current_cases)} existing cases are unchanged.",
                    icon="ℹ️",
                )
                rows = []
                for case in new_cases:
                    case_id = case.get("id", case.get("case_id", ""))
                    inp = case.get("input", case)
                    rubric = (case.get("expected_output") or case.get("rubric") or {})
                    if isinstance(rubric, dict) and "rubric" in rubric:
                        rubric = rubric["rubric"]
                    notes = rubric.get("notes", "")
                    rows.append({
                        "Status": "✦ New" if case_id not in current_ids else "Modified",
                        "ID": case_id,
                        "Customer": inp.get("customer_id", ""),
                        "Product": inp.get("product_id", ""),
                        "CTA": rubric.get("expected_cta", ""),
                        "Tone": rubric.get("expected_tone", ""),
                        "Notes": notes[:80] + "…" if len(notes) > 80 else notes,
                    })
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        if applied:
            st.caption("Changes applied locally. Run Step 3 to measure improvement.")

    def tab_langfuse() -> None:
        embeds.render_langfuse_panel(title="Langfuse — project overview", key_prefix="step2_lf")

    with ui.story_section("Observe & results"):
        embeds.render_horizontal_tabs(
            ["Run logs", "Proposal", "Langfuse"],
            [tab_logs, tab_proposal, tab_langfuse],
        )
