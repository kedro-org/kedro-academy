"""Agent selector — native st.pills with SVG icons injected via CSS ::before.

CSS in styles.py uses [data-baseweb="button-group"] button:nth-of-type(N)::before
to prepend a coloured icon square (matching the header card) to each pill button.
No overlay layer needed — native st.pills handles all interaction.
"""

from __future__ import annotations

import streamlit as st

from app.data_loader import get_latest_score_for_agent

# JS injected into the parent document to wrap the plain-text score in a
# per-agent coloured badge that matches the campaign.html reference design.
_SCORE_BADGE_JS = r"""<script>
(function(){
  var C=[
    {bg:'#EEF2FF',fg:'#2251FF'},
    {bg:'#F5F3FF',fg:'#8B5CF6'},
    {bg:'#F0FDFA',fg:'#0F766E'}
  ];
  function apply(){
    var d=window.parent.document;
    var btns=d.querySelectorAll('[data-testid^="stBaseButton-pills"]');
    btns.forEach(function(btn,i){
      if(btn.querySelector('.rh-sc'))return;
      var c=C[i]||{bg:'#F1F5F9',fg:'#64748B'};
      var p=btn.querySelector('p');
      if(!p)return;
      var m=p.textContent.match(/^(.+?)\s{2}([\d.]+|—)$/);
      if(!m)return;
      p.innerHTML='<span>'+m[1]+'</span>'
        +'<span class="rh-sc" style="background:'+c.bg+';color:'+c.fg
        +';font-size:10px;font-weight:700;padding:1px 7px;border-radius:100px;'
        +'margin-left:6px;display:inline-flex;align-items:center;line-height:1.4;">'
        +m[2]+'</span>';
    });
  }
  apply();
  new MutationObserver(apply).observe(window.parent.document.body,{childList:true,subtree:true});
})();
</script>"""

AGENTS: dict[str, dict] = {
    "b2b_sales": {
        "label": "B2B Sales",
        "subtitle": "Enterprise Outreach Agent",
        "icon": "briefcase",
        "color": "#2251FF",
        "bg": "#EEF2FF",
        "score_bg": "#DCFCE7",
        "score_fg": "#15803D",
        "emoji": "💼",
    },
    "consumer_mktg": {
        "label": "Consumer Marketing",
        "subtitle": "Plan & Device Offers Agent",
        "icon": "bar-chart-2",
        "color": "#8B5CF6",
        "bg": "#F5F3FF",
        "score_bg": "#F3E8FF",
        "score_fg": "#7C3AED",
        "emoji": "📊",
    },
    "customer_care": {
        "label": "Customer Care",
        "subtitle": "Support Reply Agent",
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

    if "agent_pills" not in st.session_state:
        st.session_state["agent_pills"] = selected_agent

    result = st.pills(
        "Agent",
        options=list(AGENTS.keys()),
        format_func=_label,
        label_visibility="collapsed",
        key="agent_pills",
    )
    st.iframe(_SCORE_BADGE_JS, height=1)
    return result if result is not None else selected_agent
