"""Stage 2: Scouts component."""

from __future__ import annotations

import re

import streamlit as st

from app.data_loader import get_signals

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

_SIGNAL_DESCRIPTIONS = {
    "rubric_miss": "One or more eval cases scored below the rubric threshold.",
    "low_pass_rate": "Pass rate fell below the configured minimum.",
    "high_error_rate": "Error rate exceeded acceptable bounds.",
    "score_regression": "Mean score regressed compared to the previous run.",
    "cta_miss": "CTA scorer fired below threshold on multiple cases.",
    "personalization_miss": "Personalisation scorer below threshold on multiple cases.",
}

_SCOUT_RULES = {
    "rubric_miss": "mean_per_scorer[dim] < threshold for ≥ 2 dims",
    "low_pass_rate": "pass_rate < 0.80",
    "high_error_rate": "n_errors / n_cases > 0.10",
    "score_regression": "mean_score < prev_run.mean_score - 0.02",
    "cta_miss": "mean_per_scorer['cta_present'] < 0.85",
    "personalization_miss": "mean_per_scorer['personalization'] < 0.80",
}


def _confidence_pill(confidence: str) -> str:
    mapping = {
        "high": ("background:#FEE2E2;color:#B91C1C;", "HIGH"),
        "medium": ("background:#FEF9C3;color:#92400E;", "MED"),
        "low": ("background:#F1F5F9;color:#64748B;", "LOW"),
    }
    style, label = mapping.get(str(confidence).lower(), ("background:#F1F5F9;color:#64748B;", str(confidence).upper()))
    return (
        f'<span style="{style}font-size:11px;font-weight:700;padding:2px 7px;'
        f'border-radius:100px;">{label}</span>'
    )


def render_stage_scouts(agent_id: str, run_id: str | None) -> None:
    """Render Stage 2: Scouts."""

    signals = get_signals(agent_id, run_id or "") if run_id else []
    n_signals = len(signals)
    run_id_display = run_id or "run_1"
    cmd = (
        f"kedro run --pipelines scouts "
        f"--params agent_id={agent_id},run_id={run_id_display}"
    )

    # ── Command strip ─────────────────────────────────────────────────────────
    col_cmd, col_btn = st.columns([5, 1])
    with col_cmd:
        if n_signals:
            badge_html = (
                f'<span style="background:#FEF3C7;color:#92400E;font-size:11px;font-weight:700;'
                f'padding:3px 10px;border-radius:100px;border:1px solid #FCD34D;">'
                f'⚡ {n_signals} signal{"s" if n_signals != 1 else ""} · threshold met</span>'
            )
        else:
            badge_html = (
                '<span style="background:#F0FDF4;color:#15803D;font-size:11px;font-weight:700;'
                'padding:3px 10px;border-radius:100px;border:1px solid #86EFAC;">'
                '✓ 0 signals</span>'
            )
        st.markdown(
            f"""
            <div class="command-strip">
              <div style="flex:1;min-width:0;">
                <div style="font-size:10.5px;color:#94A3B8;margin-bottom:6px;">
                  Pure Python, deterministic, no LLM — fires signals when eval thresholds are breached
                </div>
                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                  <span style="color:#4ADE80;font-family:monospace;font-size:13px;">$</span>
                  <span class="command-text">{cmd}</span>
                </div>
                <div style="margin-top:8px;">{badge_html}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown('<div style="padding-top:4px;">', unsafe_allow_html=True)
        run_clicked = st.button(
            "▶ Run",
            key=f"run_scouts_{agent_id}",
            type="primary",
            width="stretch",
            disabled=run_id is None,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Sub-tabs ──────────────────────────────────────────────────────────────
    _logs_key = f"show_run_logs_scouts_{agent_id}"
    if run_clicked:
        st.session_state[_logs_key] = True
    _show_logs = st.session_state.pop(_logs_key, False)
    tab_viz, tab_signals, tab_logs = st.tabs(["⊞ Kedro-Viz", "◎ Signals", ">_ Run Logs"])
    if _show_logs:
        st.iframe(_SELECT_RUN_LOGS_JS, height=1)

    # ── Signals tab ───────────────────────────────────────────────────────────
    with tab_signals:
        # Explanation banner
        st.markdown(
            """
            <div style="background:#EEF2FF;border:1px solid #C7D2FE;border-radius:10px;
                        padding:14px 18px;margin-bottom:16px;">
              <div style="font-size:13px;font-weight:600;color:#3730A3;margin-bottom:4px;">
                What are Scouts?
              </div>
              <div style="font-size:13px;color:#4338CA;line-height:1.6;">
                Scout rules are deterministic Python checks that run after every evaluation.
                They inspect scores, pass rates, and error counts to decide whether a
                reflection is warranted — no LLM required.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not run_id:
            st.info("Run the campaign pipeline first to see scout results.")
        elif n_signals > 0:
            # Threshold banner
            st.markdown(
                """
                <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;
                            padding:14px 18px;margin-bottom:16px;display:flex;
                            align-items:center;gap:10px;">
                  <span style="font-size:18px;">🚨</span>
                  <div>
                    <div style="font-size:13px;font-weight:700;color:#B91C1C;">
                      Threshold met — Reflect triggered
                    </div>
                    <div style="font-size:12px;color:#DC2626;margin-top:2px;">
                      Scout rules fired on the latest evaluation run. A reflection is recommended.
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Signals table
            rows_html = ""
            for sig in signals:
                sig_type = sig.get("signal_type") or sig.get("type") or "unknown"
                confidence = sig.get("confidence") or "high"
                evidence = sig.get("evidence") or _SIGNAL_DESCRIPTIONS.get(sig_type, "—")
                rule = sig.get("rule") or _SCOUT_RULES.get(sig_type, "—")

                rows_html += f"""
                <tr>
                  <td style="padding:12px 14px;">
                    <code style="background:#F1F5F9;padding:2px 7px;border-radius:4px;
                                 font-size:12px;color:#0F172A;">{sig_type}</code>
                  </td>
                  <td style="padding:12px 14px;">{_confidence_pill(confidence)}</td>
                  <td style="padding:12px 14px;font-size:13px;color:#475569;max-width:280px;">
                    {evidence}
                  </td>
                  <td style="padding:12px 14px;">
                    <code style="font-size:11px;color:#7C3AED;background:#F5F3FF;
                                 padding:2px 6px;border-radius:4px;">{rule}</code>
                  </td>
                </tr>
                """

            st.html(f"""
<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;
            font-family:Inter,sans-serif;">
  <table style="width:100%;border-collapse:collapse;">
    <thead style="background:#F8FAFC;">
      <tr>
        <th style="padding:10px 14px;font-size:11px;font-weight:700;color:#94A3B8;
                   text-transform:uppercase;letter-spacing:0.06em;text-align:left;
                   border-bottom:1px solid #E2E8F0;">Signal Type</th>
        <th style="padding:10px 14px;font-size:11px;font-weight:700;color:#94A3B8;
                   text-transform:uppercase;letter-spacing:0.06em;text-align:left;
                   border-bottom:1px solid #E2E8F0;">Confidence</th>
        <th style="padding:10px 14px;font-size:11px;font-weight:700;color:#94A3B8;
                   text-transform:uppercase;letter-spacing:0.06em;text-align:left;
                   border-bottom:1px solid #E2E8F0;">Evidence</th>
        <th style="padding:10px 14px;font-size:11px;font-weight:700;color:#94A3B8;
                   text-transform:uppercase;letter-spacing:0.06em;text-align:left;
                   border-bottom:1px solid #E2E8F0;">Rule</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
""")

            # Unfired scouts (all known types not in signals)
            fired_types = {s.get("signal_type") or s.get("type") for s in signals}
            unfired = [t for t in _SCOUT_RULES if t not in fired_types]
            if unfired:
                st.markdown(
                    '<div style="margin-top:16px;font-size:12px;font-weight:600;color:#94A3B8;'
                    'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">'
                    "Unfired Scouts</div>",
                    unsafe_allow_html=True,
                )
                pills_html = " ".join(
                    f'<span style="background:#F8FAFC;border:1px solid #E2E8F0;color:#94A3B8;'
                    f'font-size:12px;padding:3px 10px;border-radius:100px;opacity:0.7;">'
                    f'<code style="font-size:11px;">{t}</code></span>'
                    for t in unfired
                )
                st.markdown(
                    f'<div style="display:flex;flex-wrap:wrap;gap:6px;">{pills_html}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                """
                <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;
                            padding:40px 24px;text-align:center;">
                  <div style="font-size:32px;margin-bottom:12px;">✅</div>
                  <div style="font-size:15px;font-weight:600;color:#15803D;margin-bottom:6px;">
                    No signals fired
                  </div>
                  <div style="font-size:13px;color:#166534;">
                    All scout rules passed. No reflection is required for this run.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Kedro-Viz tab ─────────────────────────────────────────────────────────
    with tab_viz:
        from app.components.kedro_viz_tab import render_kedro_viz
        render_kedro_viz(agent_id, ["scouts"], stage_key="scouts")

    # ── Run Logs tab ──────────────────────────────────────────────────────────
    with tab_logs:
        if run_clicked:
            from app import runner
            log_lines: list[str] = []
            log_placeholder = st.empty()

            def on_log(line: str) -> None:
                log_lines.append(line)
                st.session_state[f"scouts_logs_{agent_id}"] = log_lines.copy()
                clean = _ANSI_ESCAPE.sub("", "".join(log_lines[-80:]))
                log_placeholder.code(clean, language="log")

            with st.spinner("Running scouts pipeline…"):
                ok, _ = runner.run_scouts(run_id_display, agent_id, on_log=on_log)

            if ok:
                st.success("Scouts complete.")
            else:
                st.error("Scouts pipeline failed — check logs above.")
            st.session_state[_logs_key] = True
            st.cache_data.clear()
            st.rerun()
        else:
            log_lines = st.session_state.get(f"scouts_logs_{agent_id}", [])
            if log_lines:
                clean = _ANSI_ESCAPE.sub("", "".join(log_lines[-200:]))
                if clean:
                    st.code(clean, language="log")
