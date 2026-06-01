"""Streamlit entry point for the Reflection Hub.

Run with:  streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from app.styles import inject_css
from app.pages.campaign import render as render_campaign


def _make_favicon():
    """Create the Reflection Hub favicon as a PIL Image.

    Blue rounded square (#2251FF) with a white trending-up chart line —
    matches the SVG favicon in the HTML mockup exactly.
    """
    from PIL import Image, ImageDraw

    size = 64  # render at 2× for crispness; browsers scale down to 32×32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue rounded-rectangle background
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=14, fill=(34, 81, 255, 255))

    # Scale factor: SVG viewBox is 24×24, our canvas is 64×64
    s = size / 24

    w = max(3, round(2.8 * s / 24 * 3.5))   # stroke-width 2.8 in 24×24 → scaled

    # White trending-up polyline: 4,22 → 11,14 → 17,18 → 24,10
    pts = [(4 * s, 22 * s), (11 * s, 14 * s), (17 * s, 18 * s), (24 * s, 10 * s)]
    draw.line(pts, fill=(255, 255, 255, 255), width=w)

    # Arrow corner: 21,10 → 24,10 → 24,13
    pts2 = [(21 * s, 10 * s), (24 * s, 10 * s), (24 * s, 13 * s)]
    draw.line(pts2, fill=(255, 255, 255, 255), width=w)

    return img


def main() -> None:
    st.set_page_config(
        page_title="Reflection Hub",
        page_icon=_make_favicon(),
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    # Spawn Kedro-Viz as early as possible so it's ready by the time the user
    # opens the Kedro-Viz tab.  wait=False returns immediately without blocking
    # the page render; the Kedro-Viz tab handles the "starting" state.
    from app.kedro_viz_server import ensure_kedro_viz_running

    _agent = st.session_state.get("agent_id", "b2b_sales")
    ensure_kedro_viz_running(
        _ROOT,
        agent_params=f"agent_id={_agent}",
        wait=False,
    )

    render_campaign()


if __name__ == "__main__":
    main()
