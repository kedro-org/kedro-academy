"""Stage 4: Approve & Apply component."""

from __future__ import annotations

import difflib
import html
import re

import streamlit as st

from app.command_strip import caption_apply, caption_next_run
from app.data_loader import (
    get_aggregate_scores,
    get_emails,
    get_latest_run_entry,
    get_per_case_scores,
    get_proposed_prompt,
    get_proposed_skill,
    get_run_index,
    get_skill_text,
    get_system_prompt,
    is_reflection_applied,
    next_campaign_run_id,
    reflection_id_for_run,
    run_has_evaluation,
    verification_run_after_last_apply,
    next_run_id as increment_run_id,
)
from app.components.charts import dimension_delta_table_html

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[mK]")
_SELECT_RUN_LOGS_JS = (
    "<script>(function(){"
    "var d=window.parent.document;"
    "var me=Array.from(d.querySelectorAll('iframe')).find(function(f){return f.contentWindow===window;});"
    "if(!me)return;"
    "var tls=Array.from(d.querySelectorAll('[role=\"tablist\"]'));"
    "var cl=null;"
    "tls.forEach(function(tl){if(me.compareDocumentPosition(tl)&Node.DOCUMENT_POSITION_PRECEDING){cl=tl;}});"
    "if(!cl)return;"
    "var btn=Array.from(cl.querySelectorAll('button[role=\"tab\"]')).find(function(t){return t.textContent.includes('Run Logs');});"
    "if(btn)btn.click();"
    "})();</script>"
)


def _word_diff_html(before: str, after: str) -> tuple[str, str]:
    """Return (before_html, after_html) with word-level diff highlights."""
    a_words = before.split()
    b_words = after.split()
    matcher = difflib.SequenceMatcher(None, a_words, b_words, autojunk=False)
    a_parts: list[str] = []
    b_parts: list[str] = []
    _del = "background:#FFE4E4;color:#9B1C1C;border-radius:2px;padding:1px 3px;"
    _ins = "background:#D1FAE5;color:#065F46;border-radius:2px;padding:1px 3px;"
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            a_parts.extend(html.escape(w) for w in a_words[a0:a1])
            b_parts.extend(html.escape(w) for w in b_words[b0:b1])
        elif tag == "replace":
            a_parts.extend(
                f'<mark style="{_del}text-decoration:line-through;">{html.escape(w)}</mark>'
                for w in a_words[a0:a1]
            )
            b_parts.extend(
                f'<mark style="{_ins}">{html.escape(w)}</mark>'
                for w in b_words[b0:b1]
            )
        elif tag == "delete":
            a_parts.extend(
                f'<mark style="{_del}text-decoration:line-through;">{html.escape(w)}</mark>'
                for w in a_words[a0:a1]
            )
        elif tag == "insert":
            b_parts.extend(
                f'<mark style="{_ins}">{html.escape(w)}</mark>'
                for w in b_words[b0:b1]
            )
    return " ".join(a_parts), " ".join(b_parts)


def _system_content(messages: list[dict]) -> str:
    for m in messages:
        if m.get("role") == "system":
            return (m.get("content") or "").strip()
    return ""


def _has_changes(
    proposed_prompt: list[dict],
    current_prompt: list[dict],
    proposed_skill: str,
    current_skill: str,
) -> bool:
    prompt_changed = _system_content(proposed_prompt) != _system_content(current_prompt)
    skill_changed = proposed_skill.strip() != current_skill.strip()
    return prompt_changed or skill_changed


def _score_color(v: float) -> str:
    if v >= 0.85:
        return "#15803D"
    if v >= 0.70:
        return "#92400E"
    return "#B91C1C"


def _render_reflect_first_banner(run_id: str | None) -> None:
    """Prompt the user to run Reflect before Approve can proceed."""
    run_note = (
        f" for <strong>{run_id}</strong>"
        if run_id
        else ""
    )
    st.markdown(
        f"""
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
              Run the <strong>Reflect &amp; Propose</strong> stage first{run_note} to generate
              proposals. Once the meta-agent has produced its reflection, you will be
              able to review and approve the changes here.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stage_approve(
    agent_id: str,
    run_id: str | None,
    reflection_id: str | None,
    demo_state: object,
) -> None:
    """Render Stage 4: Approve & Apply."""

    latest_entry = get_latest_run_entry(agent_id) or {}
    latest_run_id = run_id or latest_entry.get("run_id")
    run_id_display = latest_run_id or "run_1"
    reflection_on_latest = (
        reflection_id_for_run(agent_id, latest_run_id) if latest_run_id else None
    )
    has_eval = bool(
        run_has_evaluation(latest_entry)
        or (latest_run_id and get_aggregate_scores(agent_id, latest_run_id))
    )
    verification_run = verification_run_after_last_apply(agent_id)
    pending_reflection = (
        reflection_on_latest
        and not is_reflection_applied(agent_id, reflection_on_latest)
    )
    needs_reflection_first = (
        has_eval
        and not reflection_on_latest
        and latest_run_id != verification_run
    )

    _logs_key = f"show_run_logs_{agent_id}"

    # ── Pending approval (reflection exists on latest run, not yet applied) ───
    if pending_reflection:
        refl_id_display = reflection_on_latest or "refl_1"
        proposed_prompt = get_proposed_prompt(agent_id, refl_id_display)
        proposed_skill = get_proposed_skill(agent_id, refl_id_display)
        current_prompt = get_system_prompt(agent_id)
        current_skill = get_skill_text(agent_id)
        changes_exist = _has_changes(proposed_prompt, current_prompt, proposed_skill, current_skill)

        apply_cmd = (
            f"kedro run --pipelines apply "
            f"--params agent_id={agent_id},reflection_id={refl_id_display}"
        )
        apply_caption = caption_apply(run_id=latest_run_id, reflection_id=refl_id_display)

        st.markdown(
            f"""
            <div class="command-strip" style="margin-bottom:16px;">
              <div style="flex:1;min-width:0;">
                <div style="font-size:10.5px;color:#94A3B8;margin-bottom:6px;">
                  {apply_caption}
                </div>
                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                  <span style="color:#4ADE80;font-family:monospace;font-size:13px;">$</span>
                  <span class="command-text">{apply_cmd}</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

        next_run_after_apply = increment_run_id(run_id_display, default="run_2")

        approve_col, note_col = st.columns([2, 4])
        with approve_col:
            approve_clicked = st.button(
                "✓ Approve & Apply",
                key=f"approve_apply_{agent_id}",
                type="primary",
                width="stretch",
                disabled=not changes_exist,
            )
        with note_col:
            if not changes_exist:
                st.caption(
                    "No changes to apply — the proposed prompt and skill are "
                    "identical to the current version."
                )

        if approve_clicked:
            from app import runner
            log_placeholder = st.empty()
            log_lines: list[str] = []

            def on_log(line: str) -> None:
                log_lines.append(line)
                st.session_state[f"apply_logs_{agent_id}"] = log_lines.copy()
                clean = _ANSI_ESCAPE.sub("", "".join(log_lines[-80:]))
                log_placeholder.code(clean, language="log")

            with st.spinner("Applying changes…"):
                ok, _ = runner.run_apply(refl_id_display, agent_id, on_log=on_log)

            if ok:
                st.success(
                    f"Apply complete — running campaign, evaluation, and scouts for "
                    f"{next_run_after_apply}…"
                )
                with st.spinner(
                    f"Running campaign + evaluation + scouts ({next_run_after_apply})…"
                ):
                    ok2, _ = runner.run_campaign_eval_scouts(
                        next_run_after_apply, agent_id, on_log=on_log
                    )
                if ok2:
                    st.success(f"Run {next_run_after_apply} complete.")
                else:
                    st.error(
                        f"Campaign pipeline failed for {next_run_after_apply} — check logs."
                    )
            else:
                st.error("Apply pipeline failed — check logs below.")
            st.session_state[_logs_key] = True
            st.rerun()
        return

    # ── Awaiting reflection on the latest eval run ────────────────────────────
    if needs_reflection_first or not has_eval:
        _render_reflect_first_banner(latest_run_id if has_eval else None)
        return

    # ── Post-apply verification (latest run is the run right after an apply) ──
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

    # ── Re-run campaign strip ─────────────────────────────────────────────────
    _default_next = next_campaign_run_id(agent_id, run_id_display)
    next_run_id = st.session_state.get(f"next_run_id_post_{agent_id}", _default_next)
    rerun_cmd = (
        f"kedro run --pipelines campaign,evaluation,scouts "
        f"--params agent_id={agent_id},run_id={next_run_id}"
    )
    rerun_caption = caption_next_run(
        run_id=next_run_id,
        action="campaign + evaluate + scouts",
        latest_run_id=run_id_display,
    )

    col_cmd, col_btn = st.columns([5, 1])
    with col_cmd:
        st.markdown(
            f"""
            <div class="command-strip">
              <div style="flex:1;min-width:0;">
                <div style="font-size:10.5px;color:#94A3B8;margin-bottom:6px;">
                  {rerun_caption}
                </div>
                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                  <span style="color:#4ADE80;font-family:monospace;font-size:13px;">$</span>
                  <span class="command-text">{rerun_cmd}</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown('<div style="padding-top:4px;">', unsafe_allow_html=True)
        rerun_clicked = st.button(
            "▶ Run",
            key=f"rerun_campaign_{agent_id}",
            type="primary",
            width="stretch",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if rerun_clicked:
        st.session_state[_logs_key] = True

    _show_logs = st.session_state.pop(_logs_key, False)
    tab_viz, tab_logs, tab_langfuse, tab_compare = st.tabs(["⊞ Kedro-Viz", ">_ Run Logs", "∿ Langfuse", "⧉ Compare Responses"])
    if _show_logs:
        st.iframe(_SELECT_RUN_LOGS_JS, height=1)

    with tab_viz:
        from app.components.kedro_viz_tab import render_kedro_viz
        render_kedro_viz(agent_id, ["apply"], stage_key="approve")

    # ── Run Logs tab ──────────────────────────────────────────────────────────
    with tab_logs:
        if rerun_clicked:
            from app import runner
            log_lines: list[str] = []
            log_placeholder = st.empty()

            def on_log(line: str) -> None:
                log_lines.append(line)
                st.session_state[f"apply_logs_{agent_id}"] = log_lines.copy()
                clean = _ANSI_ESCAPE.sub("", "".join(log_lines[-80:]))
                log_placeholder.code(clean, language="log")

            with st.spinner(f"Running campaign + evaluation + scouts ({next_run_id})…"):
                ok, _ = runner.run_campaign_eval_scouts(next_run_id, agent_id, on_log=on_log)

            if ok:
                st.success(f"Run {next_run_id} complete.")
                st.session_state[f"next_run_id_post_{agent_id}"] = increment_run_id(
                    next_run_id, default=next_run_id
                )
            else:
                st.error(f"Pipeline failed for {next_run_id} — check logs above.")
            st.session_state[_logs_key] = True
            st.rerun()

        log_lines = st.session_state.get(f"apply_logs_{agent_id}", [])
        if log_lines:
            active_filter = st.segmented_control(
                "Filter",
                options=["All", "INFO", "ERROR"],
                default="All",
                key="log_filter_approve",
                label_visibility="collapsed",
            )
            if active_filter == "INFO":
                filtered = [l for l in log_lines if "INFO" in l]
            elif active_filter == "ERROR":
                filtered = [l for l in log_lines if "ERROR" in l]
            else:
                filtered = log_lines
            clean = _ANSI_ESCAPE.sub("", "".join(filtered[-200:]))
            if clean:
                st.code(clean, language="log")
            else:
                st.caption("No matching log lines for this filter.")

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
                st.html(
                    f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;'
                    f'border-radius:10px;overflow:hidden;">{table_html}</div>'
                )

        # Case selector — keyed by human-readable case_id from task output
        emails1 = get_emails(agent_id, run1_id)
        emails2 = get_emails(agent_id, run2_id)

        def _per_case_by_output_id(agent: str, rid: str) -> dict[str, dict]:
            """Build score lookup keyed by human-readable case_id (from task output)."""
            result: dict[str, dict] = {}
            for c in get_per_case_scores(agent, rid):
                key = (c.get("output") or {}).get("case_id") or c.get("case_id") or ""
                if key:
                    result[key] = c
            return result

        per_case1 = _per_case_by_output_id(agent_id, run1_id)
        per_case2 = _per_case_by_output_id(agent_id, run2_id)

        # Only show cases that have at least one email — skip UUID-only rows
        all_cases = sorted(set(emails1) | set(emails2))

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

        # Side-by-side email panels with word-level diff on body
        email1 = emails1.get(selected_case, {})
        email2 = emails2.get(selected_case, {})
        case1_scores = per_case1.get(selected_case, {})
        case2_scores = per_case2.get(selected_case, {})

        score1_case = float(case1_scores.get("mean_score") or case1_scores.get("case_total") or 0)
        score2_case = float(case2_scores.get("mean_score") or case2_scores.get("case_total") or 0)

        body1 = email1.get("body") or email1.get("Body") or email1.get("content") or ""
        body2 = email2.get("body") or email2.get("Body") or email2.get("content") or ""
        body1_html, body2_html = _word_diff_html(body1, body2)

        email_cols = st.columns(2)
        for col, email, body_html, score_case, run_label, border_color in [
            (email_cols[0], email1, body1_html, score1_case, f"{run1_id} — Before", "#FECACA"),
            (email_cols[1], email2, body2_html, score2_case, f"{run2_id} — After", "#86EFAC"),
        ]:
            with col:
                subject = email.get("subject") or email.get("Subject") or "—"
                company = email.get("company") or email.get("customer_id") or "—"
                product = email.get("product") or email.get("product_id") or "—"
                score_display = f"{score_case:.1%}" if score_case else "—"
                sc_color = _score_color(score_case) if score_case else "#94A3B8"
                body_content = (
                    body_html if body_html.strip()
                    else '<span style="color:#94A3B8;">No email output found</span>'
                )

                st.html(
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
                        {body_content}
                      </div>
                    </div>
                    """
                )
