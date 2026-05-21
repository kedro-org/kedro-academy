"""Step 3 — Re-run & compare.

Re-triggers ``agent_run`` + ``evaluation`` with the applied prompt/skill, then
shows the before/after scoreboard alongside sample-email pairs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import streamlit as st

from app.components import _load_json, _render_pipeline_logs
from app.state import DemoState
from app import ui_components as components
from app import embeds, charts
from kedro_reflection_agent.pipelines.reflection.models import ReflectionProposal


def render_step3(
    *,
    demo: DemoState,
    root: Path,
    proposal_path: Path,
    artifact: Callable[[str, str], Path],
    reporting: Callable[[str, str], Path],
    pipeline_params: Callable[..., dict[str, str]],
    run_with_logs: Callable[..., bool],
    on_complete: Callable[[], None],
) -> None:
    done = demo.state == "run_2_done"
    components.step_heading(
        "STEP 3 — Re-run & Compare",
        done=done,
        muted=demo.state not in ("applied", "run_2_done"),
    )

    with components.story_section("Pipeline"):
        embeds.render_kedro_viz_pipeline_picker(
            project_root=str(root),
            pipelines=embeds.STEP1_PIPELINES,
            default_pipeline_id="agent_run",
            height=520,
            session_key="viz_pipeline_step3",
        )

    with components.story_section("Run"):
        st.code(
            'kedro run --pipeline agent_run --params "run_id=run_2"\n'
            'kedro run --pipeline evaluation --params "run_id=run_2"',
            language="bash",
        )
        run_clicked = st.button(
            "Re-run Generate & Evaluate",
            disabled=not demo.can_run_agent_step3(),
            type="primary",
            key="step3_run",
        )
        log_target = components.pipeline_log_slot()
        if run_clicked:
            st.session_state["step3_logs"] = []
            with st.spinner("Running Generate & Evaluate…"):
                ok = run_with_logs(
                    "agent_run",
                    pipeline_params({"run_id": "run_2"}),
                    log_target,
                    log_key="step3_logs",
                )
                if ok:
                    ok = run_with_logs(
                        "evaluation",
                        pipeline_params({"run_id": "run_2"}),
                        log_target,
                        log_key="step3_logs",
                    )
                if ok:
                    on_complete()
                    st.rerun()

    if demo.state not in ("applied", "run_2_done"):
        st.caption("Approve and apply in Step 2 before re-running.")
        return

    traces_run1 = _load_json(artifact("run_1", "trace_metadata.json")) or []
    traces_run2 = _load_json(artifact("run_2", "trace_metadata.json")) or []

    if not done:
        st.caption("Press re-run above, then the tabs below will populate.")
        return

    agg1 = _load_json(reporting("run_1", "aggregate_scores.json")) or {}
    agg2 = _load_json(reporting("run_2", "aggregate_scores.json")) or {}
    before = float(agg1.get("aggregate_score", 0))
    after = float(agg2.get("aggregate_score", 0))
    scores1 = _load_json(artifact("run_1", "case_scores.json")) or []
    scores2 = _load_json(artifact("run_2", "case_scores.json")) or []
    emails1 = {e["case_id"]: e for e in (_load_json(artifact("run_1", "emails.json")) or [])}
    emails2 = {e["case_id"]: e for e in (_load_json(artifact("run_2", "emails.json")) or [])}
    s2_map = {s["case_id"]: s for s in scores2}

    def tab_logs() -> None:
        _render_pipeline_logs("step3_logs")

    def tab_langfuse() -> None:
        embeds.render_langfuse_panel(title="Langfuse")
        st.divider()
        embeds.render_trace_comparison(
            traces_run1 if isinstance(traces_run1, list) else [],
            traces_run2 if isinstance(traces_run2, list) else [],
        )

    def tab_compare() -> None:
        components.score_headline(before, after)
        st.plotly_chart(
            charts.dimension_bar_chart(agg1.get("dimension_scores", {}), agg2.get("dimension_scores", {})),
            width="stretch",
            key="step3_dimension_bar_chart",
        )

        with st.expander("Per-case score deltas", expanded=True):
            rows = []
            for s1 in scores1:
                s2 = s2_map.get(s1["case_id"], {})
                rows.append(
                    {
                        "case_id": s1["case_id"],
                        "company": s1.get("company_name"),
                        "run_1": s1.get("total_score"),
                        "run_2": s2.get("total_score"),
                        "delta": round((s2.get("total_score") or 0) - (s1.get("total_score") or 0), 2),
                    }
                )
            import pandas as pd
            st.dataframe(
                pd.DataFrame(rows).sort_values("delta", ascending=False),
                width="stretch",
                hide_index=True,
            )

        with st.expander("Email before/after — word-level diff (worst Run 1 cases)", expanded=True):
            worst = sorted(scores1, key=lambda s: s.get("total_score", 10))[:3]
            for s1 in worst:
                cid = s1["case_id"]
                e1 = emails1.get(cid, {})
                e2 = emails2.get(cid, {})
                s2 = s2_map.get(cid, {})
                components.email_diff_cards(
                    company=s1.get("company_name", cid),
                    product=s1.get("product_name", ""),
                    subject1=e1.get("subject", ""),
                    body1=e1.get("body", ""),
                    score1=s1.get("total_score"),
                    failure_tags1=s1.get("failure_tags"),
                    subject2=e2.get("subject", ""),
                    body2=e2.get("body", ""),
                    score2=s2.get("total_score"),
                )
                st.divider()

        if (proposal_path / "proposal.json").exists():
            proposal = ReflectionProposal.model_validate(_load_json(proposal_path / "proposal.json"))
            st.markdown("**What changed in the loop**")
            components.card("Identified", "\n".join(i.issue for i in proposal.summary.identified))
            components.card("Changed", "\n".join(c.change for c in proposal.summary.fixed))

    with components.story_section("Observe & results"):
        embeds.render_horizontal_tabs(
            ["Run logs", "Langfuse", "Compare"],
            [tab_logs, tab_langfuse, tab_compare],
        )
