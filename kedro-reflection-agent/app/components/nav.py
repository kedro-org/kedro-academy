"""Top navigation bar — sticky, in-app navigation via st.button."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import streamlit as st
from app.components.icons import ic

_PROJECT_ROOT = Path(__file__).parent.parent.parent

# Injected into the parent document from inject_css() so Streamlit Emotion column
# flex rules are overridden. Same pattern as agent_selector score badges.
NAV_STYLE_JS = r"""<script>
(function () {
  var doc = window.parent.document;
  if (doc.getElementById("rh-nav-style")) { doc.getElementById("rh-nav-style").remove(); }
  var s = doc.createElement("style");
  s.id = "rh-nav-style";
  s.textContent = `
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(style),
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(#rh-app-js-hook),
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(#rh-app-js-hook) + [data-testid="stElementContainer"] {
      display: none !important;
    }
    [data-testid="stLayoutWrapper"]:has(#rh-nav-brand),
    [data-testid="stElementContainer"]:has([data-testid="stHorizontalBlock"] #rh-nav-brand) {
      position: sticky !important; top: 0 !important; z-index: 99999 !important;
      width: 100vw !important; max-width: 100vw !important;
      margin-left: calc(50% - 50vw) !important; margin-right: calc(50% - 50vw) !important;
      margin-top: 0 !important; min-height: 56px !important;
      padding: 0 !important;
      background: rgba(255,255,255,0.97) !important;
      border-bottom: 1px solid #E2E8F0 !important;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important; box-sizing: border-box !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) {
      align-items: center !important; min-height: 56px !important; gap: 4px !important;
      flex-direction: row !important; flex-wrap: nowrap !important;
      overflow-x: auto !important; scrollbar-width: none !important;
      max-width: 1280px !important; width: 100% !important;
      margin-left: auto !important; margin-right: auto !important;
      padding: 0 1.5rem !important; box-sizing: border-box !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"] {
      flex: 0 0 auto !important; width: auto !important; min-width: 0 !important;
      flex-basis: auto !important; max-width: none !important;
      display: flex !important; align-items: center !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(2) {
      margin-left: 20px !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(4) {
      margin-left: auto !important; justify-content: flex-end !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(2) .stButton > button,
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(3) .stButton > button,
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(2) [data-testid="stBaseButton-secondary"],
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(3) [data-testid="stBaseButton-secondary"] {
      font-size: 13.5px !important; font-weight: 500 !important; color: #64748B !important;
      background: transparent !important; border: none !important; border-radius: 8px !important;
      padding: 6px 12px !important; box-shadow: none !important; white-space: nowrap !important;
      width: auto !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(2) .stButton > button *,
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(3) .stButton > button * {
      color: #64748B !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand[data-page="org_overview"]) > [data-testid="stColumn"]:nth-child(2) .stButton > button,
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand[data-page="campaigns"]) > [data-testid="stColumn"]:nth-child(3) .stButton > button {
      font-weight: 600 !important; color: #2251FF !important; background: #EEF2FF !important;
      border: none !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand[data-page="org_overview"]) > [data-testid="stColumn"]:nth-child(2) .stButton > button *,
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand[data-page="campaigns"]) > [data-testid="stColumn"]:nth-child(3) .stButton > button * {
      color: #2251FF !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(4) .stButton > button,
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"]:nth-child(4) [data-testid="stBaseButton-secondary"] {
      font-size: 12.5px !important; color: #64748B !important; background: #F1F5F9 !important;
      border: 1px solid #E2E8F0 !important; border-radius: 8px !important;
      padding: 5px 10px !important; box-shadow: none !important; white-space: nowrap !important;
    }
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"] .stButton,
    [data-testid="stHorizontalBlock"]:has(#rh-nav-brand) > [data-testid="stColumn"] [data-testid="stMarkdownContainer"] {
      margin: 0 !important; padding: 0 !important;
    }
    .rh-nav-brand { display: flex !important; align-items: center !important; gap: 8px !important; min-width: 0 !important; }
    .rh-nav-logo { width: 28px !important; height: 28px !important; border-radius: 7px !important;
      background: #2251FF !important; display: flex !important; align-items: center !important;
      justify-content: center !important; flex-shrink: 0 !important; }
    .rh-nav-title { font-size: 14px !important; font-weight: 700 !important; color: #0F172A !important;
      white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
    .rh-nav-badge { font-size: 10px !important; color: #94A3B8 !important; border: 1px solid #E2E8F0 !important;
      border-radius: 4px !important; padding: 2px 6px !important; white-space: nowrap !important; }
    @media (max-width: 900px) { .rh-nav-badge { display: none !important; } }
    @media (max-width: 480px) { .rh-nav-title { display: none !important; } }
  `;
  doc.head.appendChild(s);
})();
</script>"""


def _do_reset() -> None:
    """Full demo reset: seed data + clear UI state."""
    subprocess.run(
        [sys.executable, str(_PROJECT_ROOT / "scripts" / "seed_demo.py")],
        cwd=str(_PROJECT_ROOT),
        check=False,
    )
    st.cache_data.clear()
    _keep = {"kedro_viz_proc", "kedro_viz_start_attempted"}
    for k in [k for k in st.session_state if k not in _keep]:
        del st.session_state[k]
    st.rerun()


def render_nav(current_page: str) -> None:
    """Render sticky nav row: brand | Org Overview | Campaigns | Reset."""
    logo_icon = ic("trending-up", size=14, color="#fff")

    col_brand, col_ov, col_camp, col_reset = st.columns(
        [2.5, 1.2, 1, 0.8], gap="small", vertical_alignment="center"
    )

    with col_brand:
        st.markdown(
            f"""
            <div id="rh-nav-brand" class="rh-nav-brand" data-page="{current_page}">
              <div class="rh-nav-logo">{logo_icon}</div>
              <span class="rh-nav-title">Reflection Hub</span>
              <span class="rh-nav-badge">Powered by Kedro</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_ov:
        if st.button("Org Overview", key="nav_btn_ov", type="secondary"):
            st.query_params["page"] = "org_overview"
            st.rerun()

    with col_camp:
        if st.button("Campaigns", key="nav_btn_camp", type="secondary"):
            st.query_params["page"] = "campaigns"
            st.rerun()

    with col_reset:
        if st.button(
            "↺  Reset",
            key="nav_reset_demo",
            type="secondary",
            help="Re-seed demo data and restore initial state",
        ):
            with st.spinner("Resetting demo…"):
                _do_reset()
