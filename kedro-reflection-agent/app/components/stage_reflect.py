"""Stage 3: Reflect & Propose component."""

from __future__ import annotations

import html
import json
import re

import streamlit as st

from app.data_loader import (
    get_proposed_prompt,
    get_proposed_skill,
    get_reflection_summary,
    get_skill_text,
    get_system_prompt,
)

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[mK]")
_KEDRO_VIZ_URL = "http://localhost:4141"
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


def _msg_text(messages: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"[{m.get('role', '').upper()}]\n{m.get('content', '')}"
        for m in messages
    )


def _diff_html(before: str, after: str) -> tuple[str, str]:
    """Simple word-level diff returning (before_html, after_html)."""
    import difflib

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


def _parse_summary(summary_md: str) -> tuple[list[str], list[str], list[str]]:
    """Extract Issues / Changes / Reasons from the reflection summary markdown.

    Matches the format produced by _render_summary_md in the reflection pipeline:
      ## Issues identified  → ### heading per issue (h3 title = the issue text)
      ## Changes proposed   → - **target**: change  (bullet lines)
      ## Reasons            → - reason              (bullet lines)
    """
    issues: list[str] = []
    changes: list[str] = []
    reasons: list[str] = []
    section: str = ""

    for line in summary_md.splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        # Section headers (## level)
        if stripped.startswith("## "):
            if "issue" in lower:
                section = "issues"
            elif "change" in lower or "propos" in lower:
                section = "changes"
            elif "reason" in lower:
                section = "reasons"
            else:
                section = ""
            continue

        if section == "issues":
            # Issues are rendered as ### headings
            if stripped.startswith("### "):
                item = stripped[4:].strip()
                if item:
                    issues.append(item)
        elif section in ("changes", "reasons"):
            # Changes and reasons are rendered as bullet points
            if stripped.startswith(("-", "*", "•")):
                item = stripped.lstrip("-*• ").strip()
                if item:
                    (changes if section == "changes" else reasons).append(item)

    return issues[:5], changes[:5], reasons[:5]


def render_stage_reflect(
    agent_id: str,
    run_id: str | None,
    reflection_id: str | None,
    demo_state: object,
) -> None:
    """Render Stage 3: Reflect & Propose."""

    run_id_display = run_id or "run_1"
    refl_id_display = reflection_id or "refl_1"
    cmd = (
        f"kedro run --pipelines reflection "
        f"--params run_id={run_id_display},reflection_id={refl_id_display}"
    )

    # ── Command strip ─────────────────────────────────────────────────────────
    col_cmd, col_btn = st.columns([5, 1])
    with col_cmd:
        st.markdown(
            f"""
            <div class="command-strip">
              <span style="color:#4ADE80;font-family:monospace;font-size:13px;">$</span>
              <span class="command-text">{cmd}</span>
              <span class="command-pill">meta-agent: gpt-4o</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown('<div style="padding-top:4px;">', unsafe_allow_html=True)
        run_clicked = st.button(
            "▶ Run Reflection",
            key=f"run_reflect_{agent_id}",
            type="primary",
            width="stretch",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Sub-tabs ──────────────────────────────────────────────────────────────
    _logs_key = f"show_run_logs_{agent_id}"
    if run_clicked:
        st.session_state[_logs_key] = True
    _show_logs = st.session_state.pop(_logs_key, False)
    _goto_approve = st.session_state.pop(f"goto_approve_{agent_id}", False)
    tab_viz, tab_logs, tab_langfuse, tab_proposal = st.tabs(["⊞ Kedro-Viz", ">_ Run Logs", "∿ Langfuse", "✎ Proposal"])
    if _show_logs:
        st.iframe(_SELECT_RUN_LOGS_JS, height=1)
    elif _goto_approve:
        st.iframe(
            "<script>Array.from(window.parent.document.querySelectorAll('button[role=\"tab\"]'))"
            ".find(t=>t.textContent.includes('Approve'))?.click();</script>",
            height=1,
        )

    # ── Kedro-Viz tab ─────────────────────────────────────────────────────────
    with tab_viz:
        try:
            import urllib.request
            urllib.request.urlopen(_KEDRO_VIZ_URL, timeout=1)
            st.iframe(_KEDRO_VIZ_URL, height=520)
        except Exception:
            st.markdown(
                """
                <div style="background:#F8FAFC;border:1px dashed #CBD5E1;border-radius:10px;
                            padding:40px 24px;text-align:center;">
                  <div style="font-size:32px;margin-bottom:12px;">📊</div>
                  <div style="font-size:15px;font-weight:600;color:#0F172A;margin-bottom:6px;">
                    Kedro-Viz not running
                  </div>
                  <div style="font-size:13px;color:#64748B;margin-bottom:16px;">
                    Start the visualisation server to see the reflection pipeline graph.
                  </div>
                  <code style="background:#0F172A;color:#7DD3FC;padding:8px 16px;
                               border-radius:8px;font-size:13px;">kedro viz run</code>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Run Logs tab ──────────────────────────────────────────────────────────
    with tab_logs:
        if run_clicked:
            from app import runner
            log_placeholder = st.empty()
            log_lines: list[str] = []

            def on_log(line: str) -> None:
                log_lines.append(line)
                st.session_state[f"reflect_logs_{agent_id}"] = log_lines.copy()
                clean = _ANSI_ESCAPE.sub("", "".join(log_lines[-80:]))
                log_placeholder.code(clean, language="log")

            with st.spinner("Running reflection pipeline…"):
                ok, _ = runner.run_reflection(run_id_display, refl_id_display, agent_id, on_log=on_log)

            if ok:
                st.success("Reflection completed. Proposal ready.")
            else:
                st.error("Reflection pipeline failed — check logs above.")
            st.session_state[_logs_key] = True
            st.rerun()
        else:
            log_lines = st.session_state.get(f"reflect_logs_{agent_id}", [])
            if log_lines:
                active_filter = st.segmented_control(
                    "Filter",
                    options=["All", "INFO", "ERROR"],
                    default="All",
                    key="log_filter_reflect",
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
        if not reflection_id:
            st.info("Run the reflection pipeline to see Langfuse analytics.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Reflection Traces", "—")
            with col2:
                st.metric("LLM Cost", "—")
            with col3:
                st.metric("Input tokens", "—")
            with col4:
                st.metric("Proposals", "1" if get_reflection_summary(agent_id, reflection_id) else "—")

    # ── Proposal tab ─────────────────────────────────────────────────────────
    with tab_proposal:
        if not reflection_id:
            st.info("Run the reflection pipeline first to see the proposal.")
            return

        summary_md = get_reflection_summary(agent_id, reflection_id)
        proposed_prompt = get_proposed_prompt(agent_id, reflection_id)
        proposed_skill = get_proposed_skill(agent_id, reflection_id)
        current_prompt = get_system_prompt(agent_id)
        current_skill = get_skill_text(agent_id)

        if not summary_md and not proposed_prompt:
            st.info("No proposal found. Run the reflection pipeline to generate one.")
            return

        # Completion banner
        st.markdown(
            """
            <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:10px;
                        padding:14px 18px;margin-bottom:20px;display:flex;
                        align-items:center;gap:10px;">
              <span style="font-size:18px;">✅</span>
              <div>
                <div style="font-size:14px;font-weight:700;color:#15803D;">
                  Meta-agent reflection complete
                </div>
                <div style="font-size:13px;color:#166534;margin-top:2px;">
                  The meta-agent has analysed run outputs and proposed prompt + skill changes.
                  Review the proposal below before approving.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 3-column summary cards
        if summary_md:
            issues, changes, reasons = _parse_summary(summary_md)
            card_cols = st.columns(3)

            with card_cols[0]:
                items_html = "".join(
                    f'<li style="margin-bottom:4px;">{html.escape(i)}</li>' for i in issues
                ) or "<li style='color:#94A3B8;'>None detected</li>"
                st.markdown(
                    f"""
                    <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;
                                padding:16px;">
                      <div style="font-size:12px;font-weight:700;color:#B91C1C;
                                  text-transform:uppercase;letter-spacing:0.06em;
                                  margin-bottom:10px;">Issues Found</div>
                      <ul style="font-size:13px;color:#7F1D1D;margin:0;padding-left:16px;
                                 line-height:1.6;">
                        {items_html}
                      </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with card_cols[1]:
                items_html = "".join(
                    f'<li style="margin-bottom:4px;">{html.escape(c)}</li>' for c in changes
                ) or "<li style='color:#94A3B8;'>None proposed</li>"
                st.markdown(
                    f"""
                    <div style="background:#EEF2FF;border:1px solid #C7D2FE;border-radius:10px;
                                padding:16px;">
                      <div style="font-size:12px;font-weight:700;color:#2251FF;
                                  text-transform:uppercase;letter-spacing:0.06em;
                                  margin-bottom:10px;">Changes Proposed</div>
                      <ul style="font-size:13px;color:#1E3A8A;margin:0;padding-left:16px;
                                 line-height:1.6;">
                        {items_html}
                      </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with card_cols[2]:
                items_html = "".join(
                    f'<li style="margin-bottom:4px;">{html.escape(r)}</li>' for r in reasons
                ) or "<li style='color:#94A3B8;'>None identified</li>"
                st.markdown(
                    f"""
                    <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:10px;
                                padding:16px;">
                      <div style="font-size:12px;font-weight:700;color:#15803D;
                                  text-transform:uppercase;letter-spacing:0.06em;
                                  margin-bottom:10px;">Reasons</div>
                      <ul style="font-size:13px;color:#14532D;margin:0;padding-left:16px;
                                 line-height:1.6;">
                        {items_html}
                      </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

        # Prompt diff section
        if proposed_prompt or current_prompt:
            st.markdown(
                '<div style="font-size:14px;font-weight:700;color:#0F172A;margin-bottom:8px;">'
                "Prompt Diff</div>",
                unsafe_allow_html=True,
            )
            before_text = _msg_text(current_prompt) if current_prompt else "(no current prompt)"
            after_text = _msg_text(proposed_prompt) if proposed_prompt else "(no proposed prompt)"
            before_html, after_html = _diff_html(before_text, after_text)

            diff_cols = st.columns(2)
            with diff_cols[0]:
                st.markdown(
                    f"""
                    <div style="font-size:11px;font-weight:700;color:#94A3B8;
                                text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">
                      Current Prompt
                    </div>
                    <div class="diff-panel before"
                         style="font-size:12.5px;white-space:pre-wrap;
                                font-family:monospace;line-height:1.7;">
                      {before_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with diff_cols[1]:
                st.markdown(
                    f"""
                    <div style="font-size:11px;font-weight:700;color:#94A3B8;
                                text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">
                      Proposed Prompt
                    </div>
                    <div class="diff-panel after"
                         style="font-size:12.5px;white-space:pre-wrap;
                                font-family:monospace;line-height:1.7;">
                      {after_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Skill diff section
        if proposed_skill or current_skill:
            st.markdown(
                '<div style="font-size:14px;font-weight:700;color:#0F172A;'
                'margin-top:20px;margin-bottom:8px;">Skill Diff</div>',
                unsafe_allow_html=True,
            )
            skill_before, skill_after = _diff_html(
                current_skill or "(no current skill)",
                proposed_skill or "(no proposed skill)",
            )
            skill_cols = st.columns(2)
            with skill_cols[0]:
                st.markdown(
                    f"""
                    <div style="font-size:11px;font-weight:700;color:#94A3B8;
                                text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">
                      Current Skill
                    </div>
                    <div class="diff-panel before"
                         style="font-size:12.5px;white-space:pre-wrap;
                                font-family:monospace;line-height:1.7;">
                      {skill_before}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with skill_cols[1]:
                st.markdown(
                    f"""
                    <div style="font-size:11px;font-weight:700;color:#94A3B8;
                                text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">
                      Proposed Skill
                    </div>
                    <div class="diff-panel after"
                         style="font-size:12.5px;white-space:pre-wrap;
                                font-family:monospace;line-height:1.7;">
                      {skill_after}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Review & Approve button
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
        _, btn_col = st.columns([6, 1])
        with btn_col:
            if st.button(
                "Review & Approve →",
                key=f"goto_approve_btn_{agent_id}",
                type="primary",
                width="stretch",
            ):
                st.session_state[f"goto_approve_{agent_id}"] = True
                st.rerun()
