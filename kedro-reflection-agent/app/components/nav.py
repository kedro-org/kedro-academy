"""Top navigation bar — fixed, full-width, matches the HTML mockup."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import streamlit as st
from app.components.icons import ic

_PROJECT_ROOT = Path(__file__).parent.parent.parent


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
    """Render the fixed nav bar.

    Each interactive element uses the same anchor-hook pattern as Reset Demo:
      st.markdown(contains #anchor)   ← CSS: element-container:has(#anchor)
      st.button(...)                  ← CSS: has(#anchor) + .element-container → position:fixed

    Order:
      nav HTML      ← contains #rh-nav-reset
      Reset button  ← has(#rh-nav-reset) + .element-container → top-right
      st.markdown   ← contains #rh-nav-ov
      Org Ov button ← has(#rh-nav-ov)  + .element-container → top-left (190px)
      st.markdown   ← contains #rh-nav-camp
      Campaigns btn ← has(#rh-nav-camp) + .element-container → top-left (310px)
    """
    logo_icon = ic("trending-up", size=14, color="#fff")

    st.markdown(
        f"""
        <style>
          .block-container {{ padding-top: 0 !important; }}
          [data-testid="stAppViewContainer"] {{ padding-top: 0 !important; }}
        </style>

        <nav id="rh-nav" style="
            position:fixed;top:0;left:0;right:0;width:100%;z-index:99999;
            background:rgba(255,255,255,0.97);backdrop-filter:blur(8px);
            border-bottom:1px solid #E2E8F0;box-shadow:0 1px 3px rgba(0,0,0,0.06);
        ">
          <div style="
              max-width:1400px;margin:0 auto;height:56px;padding:0 24px;
              display:flex;align-items:center;gap:8px;
          ">
            <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
              <div style="width:28px;height:28px;border-radius:7px;background:#2251FF;
                          display:flex;align-items:center;justify-content:center;">{logo_icon}</div>
              <span style="font-size:14px;font-weight:700;color:#0F172A;
                           letter-spacing:-0.02em;">Reflection Hub</span>
              <span style="font-size:10px;font-weight:600;color:#94A3B8;
                           border:1px solid #E2E8F0;border-radius:4px;
                           padding:2px 6px;letter-spacing:0.02em;white-space:nowrap;">
                Powered by Kedro
              </span>
            </div>
          </div>
        </nav>

        <div style="height:68px;"></div>
        <div id="rh-nav-reset" style="display:none"></div>
        """,
        unsafe_allow_html=True,
    )

    # Reset Demo ─ CSS hook: has(#rh-nav-reset) + .element-container
    if st.button("↺  Reset Demo", key="nav_reset_demo",
                 help="Re-seed demo data and restore initial state"):
        with st.spinner("Resetting demo…"):
            _do_reset()

    # The anchor ID encodes active/inactive — CSS targets each ID separately.
    # Both buttons are type="secondary" to avoid any global primary CSS conflict.
    ov_anchor = "rh-nav-ov-active" if current_page == "org_overview" else "rh-nav-ov"
    st.markdown(f'<div id="{ov_anchor}" style="display:none"></div>',
                unsafe_allow_html=True)
    if st.button("Org Overview", key="nav_btn_ov"):
        st.query_params["page"] = "org_overview"
        st.rerun()

    camp_anchor = "rh-nav-camp-active" if current_page == "campaigns" else "rh-nav-camp"
    st.markdown(f'<div id="{camp_anchor}" style="display:none"></div>',
                unsafe_allow_html=True)
    if st.button("Campaigns", key="nav_btn_camp"):
        st.query_params["page"] = "campaigns"
        st.rerun()
