"""Stage 4: Approve & Apply component."""

from __future__ import annotations

import html
import re

import streamlit as st

from app.data_loader import (
    get_aggregate_scores,
    get_apply_history,
    get_emails,
    get_per_case_scores,
    get_proposed_prompt,
    get_proposed_skill,
    get_run_index,
    get_skill_text,
    get_system_prompt,
)
from app.components.charts import dimension_delta_table_html

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[mK]")


def _score_color(v: float) -> str:
    if v >= 0.85:
        return "#15803D"
    if v >= 0.70:
        return "#92400E"
    return "#B91C1C"


def render_stage_approve(
    agent_id: str,
    run_id: str | None,
    reflection_id: str | None,
    demo_state: object,
) -> None:
    """Render Stage 4: Approve & Apply."""

    refl_id_display = reflection_id or "refl_1"
    run_id_display = run_id or "run_1"

    # Check if already applied
    apply_history = get_apply_history()
    already_applied = any(
        h.get("reflection_id") == refl_id_display for h in apply_history
    )

    # ── Approval gate banner ──────────────────────────────────────────────────
    if not already_applied:
        if reflection_id:
            # Reflection run exists — show active approval gate
            proposed_prompt = get_proposed_prompt(reflection_id) if reflection_id else []
            proposed_skill = get_proposed_skill(reflection_id) if reflection_id else ""
            current_prompt = get_system_prompt(agent_id)

            prompt_pill = ""
            if proposed_prompt or current_prompt:
                pv_before = 1
                pv_after = pv_before + 1
                prompt_pill = (
                    f'<span style="background:#EEF2FF;color:#2251FF;font-size:11px;'
                    f'font-weight:600;padding:3px 10px;border-radius:100px;'
                    f'border:1px solid #BFDBFE;">'
                    f'Prompt v{pv_before}→v{pv_after}</span>'
                )

            skill_pill = ""
            if proposed_skill:
                skill_pill = (
                    '<span style="background:#F0FDFA;color:#0F766E;font-size:11px;'
                    'font-weight:600;padding:3px 10px;border-radius:100px;'
                    'border:1px solid #99F6E4;">'
                    'Skill updated</span>'
                )

            run_index = get_run_index()
            agent_runs = [r for r in run_index if r.get("agent_id") == agent_id]
            latest_run = (
                sorted(agent_runs, key=lambda r: (r.get("started_at") or ""), reverse=True)[0]
                if agent_runs
                else {}
            )
            n_eval_cases = latest_run.get("n_cases") or 0
            cases_pill = (
                f'<span style="background:#F3E8FF;color:#7C3AED;font-size:11px;'
                f'font-weight:600;padding:3px 10px;border-radius:100px;'
                f'border:1px solid #DDD6FE;">'
                f'+{n_eval_cases} eval cases</span>'
                if n_eval_cases
                else ""
            )

            st.markdown(
                f"""
                <div style="background:#FFFBEB;border:2px solid #FCD34D;border-radius:12px;
                            padding:20px 24px;margin-bottom:16px;
                            display:flex;align-items:flex-start;gap:16px;">
                  <div style="width:36px;height:36px;border-radius:10px;background:#FDE68A;
                               display:flex;align-items:center;justify-content:center;
                               flex-shrink:0;font-size:20px;">👋</div>
                  <div style="flex:1;min-width:0;">
                    <div style="font-weight:700;color:#92400E;font-size:15px;margin-bottom:6px;">
                      ✋ Human Approval Required
                    </div>
                    <div style="font-size:13px;color:#78350F;margin-bottom:12px;line-height:1.6;">
                      3 proposals ready to apply. Approving will trigger
                      <code style="background:#FEF3C7;padding:1px 5px;border-radius:3px;
                                   font-size:11px;">kedro run --pipelines apply</code>,
                      then re-run campaign + evaluation to produce the next run.
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;">
                      {prompt_pill}{skill_pill}{cases_pill}
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            approve_col, _ = st.columns([1, 4])
            with approve_col:
                approve_clicked = st.button(
                    "✓ Approve & Apply",
                    key=f"approve_apply_{agent_id}",
                    type="primary",
                    width="stretch",
                )

            if approve_clicked:
                from app import runner
                log_placeholder = st.empty()
                log_lines: list[str] = []

                def on_log(line: str) -> None:
                    log_lines.append(line)
                    st.session_state["apply_logs"] = log_lines.copy()
                    clean = _ANSI_ESCAPE.sub("", "".join(log_lines[-80:]))
                    log_placeholder.code(clean, language="log")

                with st.spinner("Applying changes…"):
                    ok, _ = runner.run_apply(refl_id_display, on_log=on_log)

                if ok:
                    st.success("Changes applied successfully. Ready for run 2.")
                else:
                    st.error("Apply pipeline failed — check logs below.")
                st.rerun()

        else:
            # No reflection run yet — show waiting state gate
            st.markdown(
                """
                <div style="background:#FFFBEB;border:2px solid #FCD34D;border-radius:12px;
                            padding:20px 24px;margin-bottom:16px;
                            display:flex;align-items:flex-start;gap:16px;">
                  <div style="width:36px;height:36px;border-radius:10px;background:#FDE68A;
                               display:flex;align-items:center;justify-content:center;
                               flex-shrink:0;font-size:20px;">✋</div>
                  <div style="flex:1;min-width:0;">
                    <div style="font-weight:700;color:#92400E;font-size:15px;margin-bottom:6px;">
                      Human Approval Required
                    </div>
                    <div style="font-size:13px;color:#78350F;line-height:1.6;">
                      Run the <strong>Reflect &amp; Propose</strong> stage first to generate
                      proposals. Once the meta-agent has produced its reflection, you will be
                      able to review and approve the changes here.
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        return  # Don't show post-approval tabs until applied

    # ── Post-approval: show tabs ──────────────────────────────────────────────
    st.markdown(
        """
        <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:10px;
                    padding:12px 16px;margin-bottom:16px;display:flex;
                    align-items:center;gap:10px;">
          <span style="font-size:16px;">✅</span>
          <span style="font-size:14px;font-weight:600;color:#15803D;">
            Changes applied — prompt and skill updated.
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_viz, tab_logs, tab_langfuse, tab_compare = st.tabs(["⊞ Kedro-Viz", ">_ Run Logs", "∿ Langfuse", "⧉ Compare Responses"])

    # ── Kedro-Viz tab ─────────────────────────────────────────────────────────
    with tab_viz:
        from app.components.kedro_viz_tab import render_kedro_viz
        render_kedro_viz(agent_id, ["apply"], stage_key="approve")

    # ── Run Logs tab ──────────────────────────────────────────────────────────
    with tab_logs:
        log_lines: list[str] = st.session_state.get("apply_logs", [])
        clean = _ANSI_ESCAPE.sub("", "".join(log_lines[-200:])) or "No log output yet."
        st.code(clean, language="log")

    # ── Langfuse tab ─────────────────────────────────────────────────────────
    with tab_langfuse:
        run_index = get_run_index()
        agent_runs = sorted(
            [r for r in run_index if r.get("agent_id") == agent_id],
            key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
        )
        run2 = agent_runs[-1] if agent_runs else {}
        run1 = agent_runs[-2] if len(agent_runs) >= 2 else {}

        score2 = float(run2.get("mean_score") or 0)
        score1 = float(run1.get("mean_score") or 0)
        delta = score2 - score1
        delta_str = f"+{delta:.1%}" if delta >= 0 else f"{delta:.1%}"
        pv = run2.get("prompt_version") or "—"

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Apply Traces", str(run2.get("n_cases") or "—"))
        with col2:
            st.metric(
                f"Run 2 Score",
                f"{score2:.1%}" if score2 else "—",
                delta=delta_str if score1 and score2 else None,
            )
        with col3:
            st.metric("Prompt Version", f"v{pv}")
        with col4:
            st.metric("Eval Cases", str(run2.get("n_cases") or "—"))

    # ── Compare Responses tab ─────────────────────────────────────────────────
    with tab_compare:
        run_index = get_run_index()
        agent_runs = sorted(
            [r for r in run_index if r.get("agent_id") == agent_id],
            key=lambda r: (r.get("started_at") or "", r.get("run_seq", 0)),
        )

        if len(agent_runs) < 2:
            st.info("Need at least 2 runs to compare. Run the campaign pipeline again after applying changes.")
            return

        run1_meta = agent_runs[-2]
        run2_meta = agent_runs[-1]
        run1_id = run1_meta.get("run_id", "run_1")
        run2_id = run2_meta.get("run_id", "run_2")

        score1 = float(run1_meta.get("mean_score") or 0)
        score2 = float(run2_meta.get("mean_score") or 0)
        delta_val = score2 - score1
        delta_sign = f"+{delta_val:.1%}" if delta_val >= 0 else f"{delta_val:.1%}"
        delta_color = "#15803D" if delta_val >= 0 else "#B91C1C"

        # Score improvement banner
        st.markdown(
            f"""
            <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:10px;
                        padding:16px 20px;margin-bottom:16px;">
              <div style="display:flex;align-items:center;justify-content:space-between;
                          flex-wrap:wrap;gap:12px;">
                <div>
                  <div style="font-size:12px;font-weight:600;color:#94A3B8;
                               text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">
                    Score Improvement
                  </div>
                  <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-size:22px;font-weight:800;color:#64748B;">
                      {score1:.1%}
                    </span>
                    <span style="font-size:16px;color:#94A3B8;">→</span>
                    <span style="font-size:22px;font-weight:800;color:#0F172A;">
                      {score2:.1%}
                    </span>
                    <span style="font-size:18px;font-weight:800;color:{delta_color};">
                      {delta_sign}
                    </span>
                  </div>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                  <span style="font-size:12px;color:#64748B;font-weight:500;">{run1_id}</span>
                  <span style="font-size:12px;color:#94A3B8;">vs</span>
                  <span style="font-size:12px;color:#0F172A;font-weight:700;">{run2_id}</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Dimension score change table
        dims1: dict = run1_meta.get("mean_per_scorer") or {}
        dims2: dict = run2_meta.get("mean_per_scorer") or {}
        if dims1 or dims2:
            st.markdown(
                '<div style="font-size:13px;font-weight:600;color:#0F172A;margin-bottom:8px;">'
                "Dimension Breakdown</div>",
                unsafe_allow_html=True,
            )
            table_html = dimension_delta_table_html([run1_meta, run2_meta])
            if table_html:
                st.markdown(
                    f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;'
                    f'border-radius:10px;overflow:hidden;">{table_html}</div>',
                    unsafe_allow_html=True,
                )

        # Case selector
        emails1 = get_emails(agent_id, run1_id)
        emails2 = get_emails(agent_id, run2_id)
        per_case1 = {c.get("case_id"): c for c in get_per_case_scores(agent_id, run1_id)}
        per_case2 = {c.get("case_id"): c for c in get_per_case_scores(agent_id, run2_id)}

        all_cases = sorted(set(emails1) | set(emails2) | set(per_case1) | set(per_case2))

        if not all_cases:
            st.info("No email outputs found. Ensure the pipeline writes emails to the outputs directory.")
            return

        st.markdown(
            '<div style="font-size:13px;font-weight:600;color:#0F172A;'
            'margin-top:16px;margin-bottom:10px;">Select Case</div>',
            unsafe_allow_html=True,
        )

        selected_case = st.session_state.get(f"selected_case_{agent_id}", all_cases[0])

        case_cols = st.columns(min(len(all_cases), 6))
        for i, case_id in enumerate(all_cases[:6]):
            with case_cols[i]:
                is_sel = case_id == selected_case
                if st.button(
                    case_id,
                    key=f"case_btn_{agent_id}_{case_id}",
                    type="primary" if is_sel else "secondary",
                    width="stretch",
                ):
                    st.session_state[f"selected_case_{agent_id}"] = case_id
                    selected_case = case_id

        # Side-by-side email panels
        email1 = emails1.get(selected_case, {})
        email2 = emails2.get(selected_case, {})
        case1_scores = per_case1.get(selected_case, {})
        case2_scores = per_case2.get(selected_case, {})

        score1_case = float(case1_scores.get("case_total") or case1_scores.get("score") or 0)
        score2_case = float(case2_scores.get("case_total") or case2_scores.get("score") or 0)

        email_cols = st.columns(2)
        for col, email, score_case, run_label, border_color, run_id_label in [
            (email_cols[0], email1, score1_case, f"{run1_id} — Before", "#FECACA", run1_id),
            (email_cols[1], email2, score2_case, f"{run2_id} — After", "#86EFAC", run2_id),
        ]:
            with col:
                subject = email.get("subject") or email.get("Subject") or "—"
                body = email.get("body") or email.get("Body") or email.get("content") or ""
                company = email.get("company") or email.get("customer_id") or "—"
                product = email.get("product") or email.get("product_id") or "—"
                score_display = f"{score_case:.1%}" if score_case else "—"
                sc_color = _score_color(score_case) if score_case else "#94A3B8"

                st.markdown(
                    f"""
                    <div style="background:#FFFFFF;border:1.5px solid {border_color};
                                border-radius:10px;padding:16px;">
                      <div style="display:flex;justify-content:space-between;
                                  align-items:flex-start;margin-bottom:10px;">
                        <div>
                          <div style="font-size:11px;font-weight:700;color:#94A3B8;
                                      text-transform:uppercase;letter-spacing:0.06em;">
                            {html.escape(run_label)}
                          </div>
                          <div style="font-size:13px;font-weight:600;color:#0F172A;margin-top:2px;">
                            {html.escape(company)}
                          </div>
                          <div style="font-size:12px;color:#64748B;">{html.escape(product)}</div>
                        </div>
                        <span style="background:{sc_color}18;color:{sc_color};font-size:13px;
                                     font-weight:700;padding:3px 10px;border-radius:100px;">
                          {score_display}
                        </span>
                      </div>
                      <div style="font-size:13px;font-weight:600;color:#0F172A;
                                  border-left:3px solid {border_color};padding-left:8px;
                                  margin-bottom:10px;line-height:1.5;">
                        {html.escape(subject)}
                      </div>
                      <div style="font-size:12.5px;line-height:1.65;color:#334155;
                                  white-space:pre-wrap;max-height:300px;overflow-y:auto;">
                        {html.escape(body) if body else '<span style="color:#94A3B8;">No email output found</span>'}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
