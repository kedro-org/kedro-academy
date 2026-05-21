"""Step 1 — Generate emails.

Triggers ``agent_run`` + ``evaluation`` via the runner, then populates the
Pipeline / Emails / Scoreboard / Langfuse tabs from the produced artifacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import streamlit as st

from app.components import _case_scores_dataframe, _load_json, _render_pipeline_logs
from app.state import DemoState
from app import ui_components as components
from app import embeds, charts
from kedro_reflection_agent.utils.prompt_utils import is_weak_prompt, prompt_text


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

    current_prompt_path = root / "data" / "agent_run" / "prompts" / "campaign_agent_system_prompt.yaml"
    if current_prompt_path.exists():
        import yaml

        raw_prompt = yaml.safe_load(current_prompt_path.read_text(encoding="utf-8")) or {}
        if not is_weak_prompt(prompt_text(raw_prompt)):
            st.warning(
                "The active prompt is already **v2 (improved)**. Scores will not improve across runs "
                "until you click the **Reset** (top right) to restore the weak v1 prompt."
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
