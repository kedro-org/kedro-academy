"""Reusable Streamlit UI components — McKinsey / QB design system."""

from __future__ import annotations

import difflib
import html
import re
from contextlib import contextmanager
from typing import Generator

import streamlit as st

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[mK]")

# ── McKinsey / QB colour tokens ───────────────────────────────────────────────
_NAVY = "#002033"
_BLUE = "#0251AA"
_SUCCESS = "#00875A"
_BORDER = "#CBD5E0"
_BG = "#FAFAFA"
_CARD_BG = "#FFFFFF"
_TEXT = "#1A1A1A"
_MUTED = "#4A5568"

GLOBAL_CSS = f"""
<style>
  /* ── Layout ── */
  header[data-testid="stHeader"] {{ background: transparent; }}
  [data-testid="stAppViewContainer"] > .main {{
    background: {_BG};
    padding-top: 0.25rem;
  }}
  .block-container {{
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 96rem;
  }}

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {{
    background: {_NAVY} !important;
    border-right: none;
  }}
  [data-testid="stSidebar"] * {{
    color: rgba(255,255,255,0.88) !important;
  }}
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] strong {{
    color: #FFFFFF !important;
  }}
  [data-testid="stSidebar"] [data-testid="baseButton-secondary"] {{
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #FFFFFF !important;
    border-radius: 6px !important;
  }}
  [data-testid="stSidebar"] [data-testid="baseButton-secondary"]:hover {{
    background: rgba(255,255,255,0.15) !important;
  }}
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
    gap: 0.4rem;
  }}

  /* ── Primary buttons — QB blue ── */
  [data-testid="baseButton-primary"] {{
    background-color: {_BLUE} !important;
    border-color: {_BLUE} !important;
    color: #FFFFFF !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    padding: 0.45rem 1.25rem !important;
  }}
  [data-testid="baseButton-primary"]:hover {{
    background-color: #013E88 !important;
    border-color: #013E88 !important;
  }}
  [data-testid="baseButton-primary"]:disabled,
  [data-testid="baseButton-primary"][disabled] {{
    background-color: #94A3B8 !important;
    border-color: #94A3B8 !important;
    color: #FFFFFF !important;
    opacity: 0.7 !important;
  }}

  /* ── Secondary buttons ── */
  [data-testid="baseButton-secondary"] {{
    border-color: {_BORDER} !important;
    color: {_TEXT} !important;
    border-radius: 6px !important;
  }}

  /* ── Tabs ── */
  [data-testid="stTabs"] [data-baseweb="tab-list"] {{
    gap: 0;
    border-bottom: 1px solid {_BORDER};
    background: transparent;
  }}
  [data-testid="stTabs"] [data-baseweb="tab"] {{
    font-size: 13px;
    font-weight: 500;
    color: {_MUTED} !important;
    padding: 0.5rem 1rem;
    border-bottom: 2px solid transparent;
    background: transparent !important;
  }}
  [data-testid="stTabs"] [aria-selected="true"] {{
    color: {_BLUE} !important;
    border-bottom: 2px solid {_BLUE} !important;
  }}

  /* ── Metrics ── */
  [data-testid="stMetric"] {{
    background: {_CARD_BG};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 14px 18px;
  }}
  [data-testid="stMetricLabel"] {{
    font-size: 12px !important;
    color: {_MUTED} !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  [data-testid="stMetricValue"] {{
    font-size: 22px !important;
    font-weight: 700 !important;
    color: {_TEXT} !important;
  }}

  /* ── Code / logs ── */
  div[data-testid="stCode"] pre {{
    white-space: pre-wrap;
    overflow-x: auto;
    font-size: 11.5px;
    line-height: 1.6;
    border-radius: 6px;
  }}
  div[data-testid="stCode"] {{
    width: 100%;
  }}

  /* ── Divider ── */
  hr {{
    border: none;
    border-top: 1px solid {_BORDER};
    margin: 1.5rem 0;
  }}

  /* ── Step pill ── */
  .step-pill-done {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: {_SUCCESS};
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    margin-left: 10px;
    vertical-align: middle;
    letter-spacing: 0.03em;
  }}
  .step-pill-pending {{
    display: inline-flex;
    align-items: center;
    background: #E2E8F0;
    color: {_MUTED};
    font-size: 11px;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 20px;
    margin-left: 10px;
    vertical-align: middle;
  }}

  /* ── Hide sidebar toggle ── */
  [data-testid="collapsedControl"] {{ display: none !important; }}

  /* ── Top accent bar ── */
  .top-accent-bar {{
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, {_NAVY} 0%, {_BLUE} 100%);
    z-index: 99999;
  }}

  /* ── Fixed footer ── */
  .app-footer {{
    position: fixed;
    bottom: 0; left: 0; right: 0;
    height: 48px;
    background: {_NAVY};
    border-top: 1px solid rgba(255,255,255,0.08);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 28px;
    z-index: 9998;
  }}

  /* ── Bottom padding so footer doesn't overlap content ── */
  .block-container {{
    padding-bottom: 80px !important;
  }}

  /* ── Info/warning callouts ── */
  [data-testid="stAlert"] {{
    border-radius: 6px !important;
    font-size: 14px !important;
  }}

  /* ── Sticky workflow bar ── */
  .wf-bar-wrapper {{
    background: {_BG};
    padding: 6px 0;
  }}
</style>
"""


def inject_global_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def inject_page_chrome(kedro_avatar_url: str | None = None) -> None:
    """Inject fixed top accent bar and footer. Call once, early in the page."""
    logo = (
        f'<img src="{kedro_avatar_url}" width="18" height="18" '
        f'style="border-radius:3px;vertical-align:middle;margin-right:8px;" />'
        if kedro_avatar_url else ""
    )
    st.markdown(
        f"""
        <div class="top-accent-bar"></div>
        <div class="app-footer">
          <span style="display:flex;align-items:center;color:rgba(255,255,255,0.75);font-size:12px;">
            {logo}B2B Campaign Agent &mdash; Reflection Loop
          </span>
          <span style="color:rgba(255,255,255,0.35);font-size:11px;letter-spacing:0.04em;">
            DEMO ENVIRONMENT &nbsp;&middot;&nbsp; KEDRO &nbsp;&middot;&nbsp; &copy; 2026
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(kedro_avatar_url: str | None = None) -> None:
    kedro_badge = ""
    if kedro_avatar_url:
        kedro_badge = f"""
        <div style="display:inline-flex;align-items:center;gap:6px;margin-bottom:10px;">
          <img src="{kedro_avatar_url}" width="18" height="18"
               style="border-radius:3px;vertical-align:middle;" />
          <span style="font-size:11px;font-weight:700;letter-spacing:0.1em;
                       color:{_BLUE};text-transform:uppercase;vertical-align:middle;">
            Kedro
          </span>
        </div>"""
    st.markdown(
        f"""
        <div style="padding:0 0 1.25rem 0;border-bottom:2px solid {_NAVY};margin-bottom:1.5rem;">
          {kedro_badge}
          <h1 style="font-size:26px;font-weight:700;color:{_NAVY};margin:0 0 4px 0;
                     letter-spacing:-0.02em;">
            B2B Campaign Agent&nbsp;&mdash;&nbsp;Reflection Loop
          </h1>
          <p style="font-size:14px;color:{_MUTED};margin:0;">
            A telco B2B outreach agent that reflects on traces, scores, and prompts to improve itself.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workflow_bar(current: int) -> None:
    """Horizontal step progress bar. current = index of the active step (0-based)."""
    steps = [
        ("01", "Generate & Evaluate"),
        ("02", "Reflect & Apply"),
        ("03", "Compare Runs"),
    ]
    parts: list[str] = []
    for i, (num, label) in enumerate(steps):
        if i < current:
            # completed
            circle = f'<div style="width:28px;height:28px;border-radius:50%;background:{_SUCCESS};display:flex;align-items:center;justify-content:center;flex-shrink:0;"><span style="color:#fff;font-size:12px;font-weight:700;">✓</span></div>'
            num_style = f"color:{_SUCCESS};font-weight:700;"
            label_style = f"color:{_MUTED};"
        elif i == current:
            # active
            circle = f'<div style="width:28px;height:28px;border-radius:50%;background:{_BLUE};display:flex;align-items:center;justify-content:center;flex-shrink:0;border:2px solid {_BLUE};"><span style="color:#fff;font-size:11px;font-weight:700;">{num}</span></div>'
            num_style = f"color:{_BLUE};font-weight:700;"
            label_style = f"color:{_TEXT};font-weight:600;"
        else:
            # upcoming
            circle = f'<div style="width:28px;height:28px;border-radius:50%;background:#F0F4F8;border:1.5px solid {_BORDER};display:flex;align-items:center;justify-content:center;flex-shrink:0;"><span style="color:{_MUTED};font-size:11px;font-weight:600;">{num}</span></div>'
            num_style = f"color:{_MUTED};"
            label_style = f"color:{_MUTED};"

        step_html = f"""
        <div style="display:flex;align-items:center;gap:10px;">
          {circle}
          <div>
            <div style="font-size:10px;letter-spacing:0.08em;text-transform:uppercase;{num_style}">
              Step {num}
            </div>
            <div style="font-size:13px;{label_style}">{label}</div>
          </div>
        </div>"""
        parts.append(step_html)

        if i < len(steps) - 1:
            connector_color = _SUCCESS if i < current else _BORDER
            parts.append(
                f'<div style="flex:1;height:1.5px;background:{connector_color};margin:0 8px;min-width:24px;"></div>'
            )

    st.markdown(
        f"""
        <div class="wf-bar-wrapper">
          <div class="wf-bar-container" style="display:flex;align-items:center;padding:16px 20px;
                      background:{_CARD_BG};border:1px solid {_BORDER};
                      border-radius:10px;margin-bottom:1.5rem;gap:8px;
                      box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            {"".join(parts)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def step_heading(label: str, done: bool = False, muted: bool = False) -> None:
    color = _MUTED if muted else _NAVY
    border = _BORDER if muted else _BLUE
    pill = (
        f'<span class="step-pill-done">&#10003;&nbsp;Done</span>'
        if done
        else (
            '<span class="step-pill-pending">Waiting</span>'
            if muted
            else ""
        )
    )
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;padding:12px 16px;
                    border-left:4px solid {border};background:{_CARD_BG};
                    border-radius:0 6px 6px 0;margin-bottom:1rem;
                    border-top:1px solid {_BORDER};border-right:1px solid {_BORDER};
                    border-bottom:1px solid {_BORDER};">
          <span style="font-size:15px;font-weight:700;color:{color};letter-spacing:-0.01em;">
            {html.escape(label)}
          </span>
          {pill}
        </div>
        """,
        unsafe_allow_html=True,
    )


def update_pipeline_log(target: st.delta_generator.DeltaGenerator, lines: list[str]) -> None:
    raw = "".join(lines[-100:])
    clean = _ANSI_ESCAPE.sub("", raw)
    target.code(clean or "Waiting for pipeline output…", language="log")


def card(title: str, body: str, border_left_color: str = _BORDER) -> None:
    body_html = html.escape(body).replace("\n", "<br/>")
    st.markdown(
        f"""
        <div style="background:{_CARD_BG};border:1px solid {_BORDER};
                    border-left:4px solid {border_left_color};
                    border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:12px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.04);">
          <div style="font-size:13px;font-weight:700;color:{_MUTED};
                      text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">
            {html.escape(title)}
          </div>
          <div style="font-size:14px;line-height:1.6;color:{_TEXT};">{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_headline(before: float, after: float) -> None:
    delta = after - before
    sign = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
    delta_color = _SUCCESS if delta >= 0 else "#CC3333"
    st.markdown(
        f"""
        <div style="display:flex;justify-content:center;align-items:center;
                    gap:32px;margin:28px 0;flex-wrap:wrap;">
          <div style="background:{_CARD_BG};border:1px solid {_BORDER};border-radius:10px;
                      padding:28px 40px;text-align:center;min-width:160px;
                      box-shadow:0 1px 4px rgba(0,0,0,0.06);">
            <div style="font-size:11px;color:{_MUTED};text-transform:uppercase;
                        letter-spacing:0.08em;margin-bottom:6px;">Before &middot; Run 1</div>
            <div style="font-size:40px;font-weight:800;color:{_TEXT};line-height:1;">
              {before:.1f}
              <span style="font-size:16px;font-weight:400;color:{_MUTED};">/10</span>
            </div>
          </div>

          <div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
            <div style="font-size:20px;color:{_BORDER};">&#8594;</div>
            <div style="font-size:18px;font-weight:700;color:{delta_color};">{sign}</div>
          </div>

          <div style="background:{_CARD_BG};border:2px solid {_BLUE};border-radius:10px;
                      padding:28px 40px;text-align:center;min-width:160px;
                      box-shadow:0 2px 8px rgba(2,81,170,0.12);">
            <div style="font-size:11px;color:{_MUTED};text-transform:uppercase;
                        letter-spacing:0.08em;margin-bottom:6px;">After &middot; Run 2</div>
            <div style="font-size:40px;font-weight:800;color:{_BLUE};line-height:1;">
              {after:.1f}
              <span style="font-size:16px;font-weight:400;color:{_MUTED};">/10</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def email_card(
    company: str,
    product: str,
    subject: str,
    body: str,
    score: float | None = None,
    failure_tags: list[str] | None = None,
    passed: bool = False,
) -> None:
    score_color = (
        _SUCCESS if score is not None and score >= 7
        else ("#CC8800" if score is not None and score >= 5 else "#CC3333")
    )
    score_badge = (
        f'<span style="background:{score_color};color:#fff;border-radius:20px;'
        f'padding:3px 10px;font-size:12px;font-weight:700;">{score:.1f}/10</span>'
        if score is not None
        else ""
    )
    if passed:
        tags_html = f'<span style="color:{_SUCCESS};font-size:12px;font-weight:600;">✓ Improved</span>'
    else:
        tags_html = " ".join(
            f'<span style="background:#FEF2F2;color:#CC3333;border:1px solid #FECACA;'
            f'border-radius:4px;padding:2px 8px;font-size:11px;font-weight:500;'
            f'margin-right:4px;">{html.escape(t)}</span>'
            for t in (failure_tags or [])[:4]
        )
    preview = html.escape(body)
    st.markdown(
        f"""
        <div style="background:{_CARD_BG};border:1px solid {_BORDER};border-radius:8px;
                    padding:18px 20px;margin-bottom:12px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.05);">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;
                      margin-bottom:10px;">
            <div>
              <div style="font-size:14px;font-weight:700;color:{_TEXT};">
                {html.escape(company)}
              </div>
              <div style="font-size:12px;color:{_MUTED};margin-top:2px;">
                {html.escape(product)}
              </div>
            </div>
            {score_badge}
          </div>
          <div style="font-size:13px;font-weight:600;color:{_NAVY};
                      border-left:3px solid {_BLUE};padding-left:8px;margin-bottom:10px;">
            {html.escape(subject)}
          </div>
          <div style="font-size:13px;line-height:1.6;color:{_TEXT};
                      white-space:pre-wrap;">{preview}</div>
          <div style="margin-top:10px;">{tags_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Email diff ────────────────────────────────────────────────────────────────

def _word_diff_html(before: str, after: str) -> tuple[str, str]:
    """Word-level diff. Returns (before_html, after_html) with inline highlights."""
    a_words = before.split()
    b_words = after.split()
    matcher = difflib.SequenceMatcher(None, a_words, b_words, autojunk=False)

    a_parts: list[str] = []
    b_parts: list[str] = []

    _del = 'background:#FFE4E4;color:#9B1C1C;border-radius:2px;padding:1px 3px;'
    _ins = 'background:#D1FAE5;color:#065F46;border-radius:2px;padding:1px 3px;'

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


def email_diff_cards(
    company: str,
    product: str,
    subject1: str,
    body1: str,
    score1: float | None,
    failure_tags1: list[str] | None,
    subject2: str,
    body2: str,
    score2: float | None,
) -> None:
    """Side-by-side email comparison with word-level diff highlights."""
    subj_a, subj_b = _word_diff_html(subject1, subject2)
    body_a, body_b = _word_diff_html(body1, body2)

    st.markdown(
        f'<div style="font-size:14px;font-weight:700;color:{_NAVY};margin-bottom:4px;">'
        f"{html.escape(company)}"
        f'<span style="font-weight:400;color:{_MUTED};font-size:12px;margin-left:8px;">'
        f"{html.escape(product)}</span></div>",
        unsafe_allow_html=True,
    )

    def _score_badge(score: float | None, *, baseline: float | None = None) -> str:
        if score is None:
            return ""
        color = _SUCCESS if score >= 7 else ("#CC8800" if score >= 5 else "#CC3333")
        delta = ""
        if baseline is not None:
            d = score - baseline
            sign = f"+{d:.1f}" if d >= 0 else f"{d:.1f}"
            delta_c = _SUCCESS if d >= 0 else "#CC3333"
            delta = f'<span style="font-size:11px;color:{delta_c};margin-left:6px;">{sign}</span>'
        return (
            f'<span style="background:{color};color:#fff;border-radius:20px;'
            f'padding:2px 9px;font-size:12px;font-weight:700;">{score:.1f}/10</span>{delta}'
        )

    def _tags(tags: list[str] | None) -> str:
        if not tags:
            return ""
        return " ".join(
            f'<span style="background:#FEF2F2;color:#CC3333;border:1px solid #FECACA;'
            f'border-radius:4px;padding:1px 7px;font-size:11px;margin-right:3px;">'
            f"{html.escape(t)}</span>"
            for t in tags[:4]
        )

    legend = (
        f'<span style="background:#FFE4E4;color:#9B1C1C;border-radius:2px;padding:1px 6px;font-size:11px;">removed</span>'
        f'&nbsp;&nbsp;'
        f'<span style="background:#D1FAE5;color:#065F46;border-radius:2px;padding:1px 6px;font-size:11px;">added</span>'
    )
    st.markdown(
        f'<div style="font-size:11px;color:{_MUTED};margin-bottom:8px;">Word-level changes:&nbsp;{legend}</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    def _card(label: str, score: float | None, badge: str, subj: str,
              body: str, tags_html: str, border: str) -> None:
        st.markdown(
            f"""
            <div style="background:{_CARD_BG};border:1px solid {border};border-radius:8px;
                        padding:16px 18px;height:100%;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
              <div style="display:flex;justify-content:space-between;align-items:center;
                          margin-bottom:10px;">
                <span style="font-size:11px;font-weight:700;color:{_MUTED};
                             text-transform:uppercase;letter-spacing:0.06em;">{label}</span>
                <span>{badge}</span>
              </div>
              <div style="font-size:12px;font-weight:600;color:{_NAVY};
                          border-left:3px solid {border};padding-left:7px;
                          margin-bottom:10px;line-height:1.5;">{subj}</div>
              <div style="font-size:13px;line-height:1.65;color:{_TEXT};
                          white-space:pre-wrap;">{body}</div>
              <div style="margin-top:8px;">{tags_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col1:
        _card(
            "Run 1 — before",
            score1,
            _score_badge(score1),
            subj_a,
            body_a,
            _tags(failure_tags1),
            "#FECACA",
        )
    with col2:
        _card(
            "Run 2 — after (improved)",
            score2,
            _score_badge(score2, baseline=score1),
            subj_b,
            body_b,
            f'<span style="color:{_SUCCESS};font-size:12px;font-weight:600;">✓ Improved</span>',
            "#6EE7B7",
        )


# ── Layout helpers ────────────────────────────────────────────────────────────

@contextmanager
def story_section(heading: str) -> Generator[None, None, None]:
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{_MUTED};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin:1.25rem 0 0.75rem 0;">'
        f"{html.escape(heading)}</div>",
        unsafe_allow_html=True,
    )
    yield
    st.markdown("")


def pipeline_log_slot() -> st.delta_generator.DeltaGenerator:
    return st.empty()
