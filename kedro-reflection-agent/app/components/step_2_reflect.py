"""Step 2 — Reflect.

Triggers the ``reflection`` pipeline, renders the narrative summary (identified
/ fixed / reasons) and the three diffs (prompt, skill, proposed eval cases),
then exposes the Approve & Apply button that runs the ``apply`` pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
import streamlit as st

from app.components import _load_json, _render_pipeline_logs
from app.state import DemoState
from app import ui_components as components
from app import embeds
from kedro_reflection_agent.pipelines.reflection.models import ReflectionProposal
from kedro_reflection_agent.utils.prompt_utils import SEED_PROMPT, SEED_SKILL, prompt_text

NEUTRAL_BORDER = "#E2E2E2"
ACCENT_BORDER = "#1A1A1A"


def render_step2(
    *,
    demo: DemoState,
    root: Path,
    proposal_id: str,
    proposal_path: Path,
    reporting: Callable[[str, str], Path],
    pipeline_params: Callable[..., dict[str, str]],
    run_with_logs: Callable[..., bool],
    on_reflect: Callable[[], None],
    on_apply: Callable[[], None],
) -> None:
    reflected = demo.state in ("reflected", "applied", "run_2_done")
    applied = demo.state in ("applied", "run_2_done")
    components.step_heading(
        "STEP 2 — Reflect & Approve",
        done=reflected,
        muted=demo.state == "idle",
    )

    with components.story_section("Pipeline"):
        embeds.render_kedro_viz_pipeline_picker(
            project_root=str(root),
            pipelines=embeds.STEP2_PIPELINES,
            default_pipeline_id="reflection",
            height=480,
            session_key="viz_pipeline_step2",
        )

    with components.story_section("Run"):
        st.code(
            'kedro run --pipeline reflection --params "run_id=run_1,proposal_id=proposal_1"\n'
            'kedro run --pipeline apply --params "proposal_id=proposal_1"',
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
                "Approve & apply",
                disabled=not demo.can_apply(),
                key="step2_apply",
            )
        log_target = components.pipeline_log_slot()
        if reflect_clicked:
            st.session_state["step2_logs"] = []
            with st.spinner("Running Reflecting…"):
                ok = run_with_logs(
                    "reflection",
                    pipeline_params({"run_id": "run_1", "proposal_id": proposal_id}),
                    log_target,
                    log_key="step2_logs",
                )
                if ok:
                    on_reflect()
                    st.rerun()
        if apply_clicked:
            st.session_state["step2_logs"] = st.session_state.get("step2_logs", [])
            with st.spinner("Applying…"):
                ok = run_with_logs(
                    "apply",
                    pipeline_params({"proposal_id": proposal_id}),
                    log_target,
                    log_key="step2_logs",
                )
                if ok:
                    on_apply()
                    st.success("Prompt v2 and regression eval cases are now active.")
                    st.rerun()

    if demo.state == "idle":
        st.caption("Finish Step 1 first.")
        return
    if not (proposal_path / "proposal.json").exists():
        st.caption("Run reflection to unlock the tabs below.")
        return

    proposal = ReflectionProposal.model_validate(_load_json(proposal_path / "proposal.json"))
    agg = _load_json(reporting("run_1", "aggregate_scores.json")) or {}
    dims = agg.get("dimension_scores", {})

    def tab_logs() -> None:
        _render_pipeline_logs("step2_logs")

    def tab_proposal() -> None:
        c1, c2, c3 = st.columns(3)
        with c1:
            components.card(
                "Issues found",
                "\n".join(f"• {i.issue}" for i in proposal.summary.identified[:3]),
                NEUTRAL_BORDER,
            )
        with c2:
            components.card(
                "Planned fixes",
                "\n".join(f"• {c.change}" for c in proposal.summary.fixed[:4]),
                ACCENT_BORDER,
            )
        with c3:
            components.card(
                "Expected lift",
                f"Personalization {dims.get('personalization', 0):.1f}/10 → target +2.5\n"
                f"CTA {dims.get('cta', 0):.1f}/10 → target +2.0",
                NEUTRAL_BORDER,
            )

        st.markdown("**Prompt diff (v1 → proposed v2)**")
        components.text_diff_card(
            "Seed prompt (v1)",
            "Proposed prompt (v2)",
            prompt_text(SEED_PROMPT),
            proposal.new_system_prompt,
        )

        with st.expander("Skill diff"):
            components.text_diff_card(
                "Seed skill (v1)",
                "Proposed skill (v2)",
                SEED_SKILL,
                proposal.new_skill_file,
            )

        with st.expander("New regression eval cases"):
            new_cases = _load_json(proposal_path / "new_eval_cases.json") or []
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "case_id": c.get("case_id"),
                            "catches": c.get("reason_added"),
                            "from_case": c.get("source_failure_case_id"),
                        }
                        for c in new_cases
                    ]
                ),
                width="stretch",
                hide_index=True,
            )

        if applied:
            st.caption("Changes applied locally. Run Step 3 to measure improvement.")

    def tab_langfuse() -> None:
        embeds.render_langfuse_panel(title="Langfuse — project overview")

    with components.story_section("Observe & results"):
        embeds.render_horizontal_tabs(
            ["Run logs", "Proposal", "Langfuse"],
            [tab_logs, tab_proposal, tab_langfuse],
        )
