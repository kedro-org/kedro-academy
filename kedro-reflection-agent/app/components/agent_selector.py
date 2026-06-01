"""Agent selector — native st.pills with SVG icons injected via CSS ::before.

CSS in styles.py uses [data-baseweb="button-group"] button:nth-of-type(N)::before
to prepend a coloured icon square (matching the header card) to each pill button.
No overlay layer needed — native st.pills handles all interaction.
"""

from __future__ import annotations

import streamlit as st

from app.data_loader import get_latest_score_for_agent

AGENTS: dict[str, dict] = {
    "b2b_sales": {
        "label": "B2B Sales",
        "icon": "briefcase",
        "color": "#2251FF",
        "bg": "#EEF2FF",
        "score_bg": "#DCFCE7",
        "score_fg": "#15803D",
        "emoji": "💼",
    },
    "consumer_mktg": {
        "label": "Consumer Marketing",
        "icon": "bar-chart-2",
        "color": "#8B5CF6",
        "bg": "#F5F3FF",
        "score_bg": "#F3E8FF",
        "score_fg": "#7C3AED",
        "emoji": "📊",
    },
    "customer_care": {
        "label": "Customer Care",
        "icon": "headphones",
        "color": "#00C4B4",
        "bg": "#F0FDFA",
        "score_bg": "#CCFBF1",
        "score_fg": "#0F766E",
        "emoji": "🎧",
    },
}

AGENT_EMOJI: dict[str, str] = {k: v["emoji"] for k, v in AGENTS.items()}


def render_agent_selector(selected_agent: str) -> str:
    """Render the agent tab bar and return the selected agent_id."""

    def _label(agent_id: str) -> str:
        score = get_latest_score_for_agent(agent_id)
        score_str = f"  {score:.2f}" if score is not None else "  —"
        return f"{AGENTS[agent_id]['label']}{score_str}"

    result = st.pills(
        "Agent",
        options=list(AGENTS.keys()),
        format_func=_label,
        default=selected_agent,
        label_visibility="collapsed",
        key="agent_pills",
    )
    return result if result is not None else selected_agent
