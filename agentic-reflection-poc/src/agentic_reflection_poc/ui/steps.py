"""Per-step sections for the single-page Streamlit demo (Run → Observe → Results)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import streamlit as st

from agentic_reflection_poc.pipelines.reflection.models import ReflectionProposal
from agentic_reflection_poc.ui.state import DemoState
from agentic_reflection_poc.utils.prompt_utils import SEED_PROMPT, SEED_SKILL, is_weak_prompt, prompt_text
from agentic_reflection_poc.ui import charts, components, embeds

NEUTRAL_BORDER = "#E2E2E2"
ACCENT_BORDER = "#1A1A1A"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


_SCOREBOARD_COLUMNS = [
    "case_id",
    "company_name",
    "product_name",
    "total_score",
    "failure_tags",
]


def _case_scores_dataframe(case_scores: list[dict[str, Any]]) -> pd.DataFrame:
    if not case_scores:
        return pd.DataFrame(columns=_SCOREBOARD_COLUMNS)
    df = pd.DataFrame(case_scores)
    for col in _SCOREBOARD_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[_SCOREBOARD_COLUMNS]


def _render_pipeline_logs(session_key: str) -> None:
    lines = st.session_state.get(session_key) or []
    if lines:
        st.code("".join(lines[-200:]), language="log")
    else:
        st.caption("Pipeline logs appear here after you run a step.")


def render_step1(
    *,
    demo: DemoState,
    root: Path,
    artifact: Callable[[str, str], Path],
    reporting: Callable[[str, str], Path],
    pipeline_params: Callable[..., dict[str, str]],
    run_with_logs: Callable[..., bool],
    on_complete: Callable[[], None],
) -> None:
    done = demo.state != "idle"
    components.step_heading("STEP 1 — Generate & Evaluate", done=done)

    current_prompt_path = root / "data" / "prompts" / "agent_run" / "campaign_agent_system_prompt.yaml"
    if current_prompt_path.exists():
        import yaml

        raw_prompt = yaml.safe_load(current_prompt_path.read_text(encoding="utf-8")) or {}
        if not is_weak_prompt(prompt_text(raw_prompt)):
            st.warning(
                "The active prompt is already **v2 (improved)**. Scores will not improve across runs "
                "until you click the **Reset Demo** (top right) to restore the weak v1 prompt."
            )

    with components.story_section("Pipeline"):
        embeds.render_kedro_viz_pipeline_picker(
            project_root=str(root),
            pipelines=embeds.STEP1_PIPELINES,
            default_pipeline_id="agent_run",
            height=520,
            session_key="viz_pipeline_step1",
        )

    agg = _load_json(reporting("run_1", "aggregate_scores.json")) or {} if done else {}

    with components.story_section("Run"):
        st.code(
            'kedro run --pipeline agent_run --params "run_id=run_1"\n'
            'kedro run --pipeline evaluation --params "run_id=run_1"',
            language="bash",
        )
        c1, c2, c3, c4 = st.columns([1.2, 0.1, 1, 1])
        with c1:
            run_clicked = st.button(
                "Run Generate & Evaluate",
                disabled=not demo.can_run_agent_step1(),
                type="primary",
                key="step1_run",
            )
        with c3:
            st.metric("Aggregate score", f"{agg.get('aggregate_score', 0):.1f}/10" if done else "—")
        with c4:
            st.metric("Cases", len(_load_json(artifact("run_1", "case_scores.json")) or []) if done else "—")

        log_target = components.pipeline_log_slot()
        if run_clicked:
            st.session_state["step1_logs"] = []
            with st.spinner("Running Generate & Evaluate…"):
                ok = run_with_logs(
                    "agent_run",
                    pipeline_params({"run_id": "run_1"}),
                    log_target,
                    log_key="step1_logs",
                )
                if ok:
                    ok = run_with_logs(
                        "evaluation",
                        pipeline_params({"run_id": "run_1"}),
                        log_target,
                        log_key="step1_logs",
                    )
                if ok:
                    on_complete()
                    st.rerun()

    if not done:
        st.caption("Complete this step to unlock the tabs below.")
        return

    emails = _load_json(artifact("run_1", "emails.json")) or []
    case_scores = _load_json(artifact("run_1", "case_scores.json")) or []
    traces = _load_json(artifact("run_1", "trace_metadata.json")) or []
    aggregate = _load_json(reporting("run_1", "aggregate_scores.json")) or {}
    score_map = {s["case_id"]: s for s in case_scores}
    dims = aggregate.get("dimension_scores", {})

    def tab_logs() -> None:
        _render_pipeline_logs("step1_logs")

    def tab_scoreboard() -> None:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Aggregate", f"{aggregate.get('aggregate_score', 0):.1f} / 10")
        m2.metric("Personalization", f"{dims.get('personalization', 0):.1f}")
        m3.metric("CTA quality", f"{dims.get('cta', 0):.1f}")
        m4.metric("Emails", len(emails))

        st.plotly_chart(
            charts.failure_tag_chart(aggregate.get("failure_tag_counts", {})),
            width="stretch",
            key="step1_failure_tag_chart",
        )
        st.dataframe(
            _case_scores_dataframe(case_scores),
            width="stretch",
            hide_index=True,
        )

        st.markdown("**Sample emails (lowest scores)**")
        ranked = sorted(
            emails,
            key=lambda e: score_map.get(e["case_id"], {}).get("total_score", 10),
        )
        for email in ranked[:3]:
            sc = score_map.get(email["case_id"], {})
            components.email_card(
                sc.get("company_name", ""),
                sc.get("product_name", ""),
                email.get("subject", ""),
                email.get("body", ""),
                score=sc.get("total_score"),
                failure_tags=sc.get("failure_tags"),
            )

    def tab_langfuse() -> None:
        embeds.render_langfuse_panel(
            traces if isinstance(traces, list) else None,
            title="Langfuse — Run 1",
        )

    with components.story_section("Observe & results"):
        embeds.render_horizontal_tabs(
            ["Run logs", "Scoreboard", "Langfuse"],
            [tab_logs, tab_scoreboard, tab_langfuse],
        )


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
