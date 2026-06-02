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
    """Render the fixed nav bar and the Reset Demo button inside it.

    The nav is plain HTML (position:fixed).  The Reset button is a native
    st.button rendered immediately after the nav's st.markdown call — making
    the two element-containers adjacent siblings.  CSS gives the button's
    element-container `position:fixed` so it floats into the nav's right side.
    The anchor div `#rh-nav-reset` embedded in the nav markdown is the CSS hook.
    """
    logo_icon = ic("trending-up", size=14, color="#fff")

    # The hidden anchor `#rh-nav-reset` at the end of this markdown is the CSS
    # hook for targeting the *next* element-container (the Reset button).
    st.markdown(
        f"""
        <style>
          .block-container {{ padding-top: 0 !important; }}
          [data-testid="stAppViewContainer"] {{ padding-top: 0 !important; }}
        </style>

        <nav id="rh-nav" style="
            position:fixed;top:0;left:0;right:0;
            width:100%;z-index:99999;
            background:rgba(255,255,255,0.97);
            backdrop-filter:blur(8px);
            border-bottom:1px solid #E2E8F0;
            box-shadow:0 1px 3px rgba(0,0,0,0.06);
        ">
          <div style="
              max-width:1400px;margin:0 auto;
              height:56px;padding:0 24px;
              display:flex;align-items:center;gap:8px;
          ">
            <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;margin-right:16px;">
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
            <div style="display:flex;align-items:center;gap:2px;">
              <span style="display:inline-flex;align-items:center;padding:6px 12px;
                           border-radius:8px;font-size:13.5px;
                           font-weight:{'600' if current_page == 'org_overview' else '500'};
                           color:{'#2251FF' if current_page == 'org_overview' else '#64748B'};
                           background:{'#EEF2FF' if current_page == 'org_overview' else 'transparent'};">
                Org Overview
              </span>
              <span style="display:inline-flex;align-items:center;padding:6px 12px;
                           border-radius:8px;font-size:13.5px;
                           font-weight:{'600' if current_page == 'campaigns' else '500'};
                           color:{'#2251FF' if current_page == 'campaigns' else '#64748B'};
                           background:{'#EEF2FF' if current_page == 'campaigns' else 'transparent'};">
                Campaigns
              </span>
            </div>
          </div>
        </nav>

        <div style="height:68px;"></div>
        <div id="rh-nav-reset" style="display:none"></div>
        """,
        unsafe_allow_html=True,
    )

    # This st.button call is immediately adjacent to the nav markdown above —
    # CSS targets `.element-container:has(#rh-nav-reset) + .element-container`
    # and fixes it into the top-right corner of the nav bar.
    if st.button("↺  Reset Demo", key="nav_reset_demo", help="Re-seed demo data and restore initial state"):
        with st.spinner("Resetting demo…"):
            _do_reset()
