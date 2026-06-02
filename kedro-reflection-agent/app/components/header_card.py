"""Campaign header card — matches the HTML mockup with Lucide icons."""

from __future__ import annotations

import streamlit as st

from app.components.agent_selector import AGENTS
from app.components.icons import ic
from app.data_loader import (
    get_apply_history,
    get_system_prompt,
    get_targets,
)

_DESCRIPTIONS: dict[str, str] = {
    "b2b_sales": (
        "Generates personalised B2B outreach emails for enterprise telco customers. "
        "The agent is evaluated against a rubric covering writing quality, personalisation depth, "
        "groundedness, and CTA clarity — then reflects on its own failures to propose prompt "
        "and skill improvements."
    ),
    "consumer_mktg": (
        "Creates personalised upgrade offer messages for consumer subscribers. "
        "Evaluated against tone, offer relevance, personalisation, and CTA clarity — "
        "then reflects to improve messaging quality and conversion."
    ),
    "customer_care": (
        "Writes empathetic support replies for customer issues. "
        "Evaluated against tone, empathy opener, resolution clarity, and action commitment — "
        "then reflects to improve response quality and customer satisfaction."
    ),
}


def render_header_card(agent_id: str, run_index: list[dict]) -> None:
    """Render the campaign header card for *agent_id*."""
    cfg = AGENTS.get(agent_id, {})
    label = cfg.get("label", agent_id)
    icon_name = cfg.get("icon", "briefcase")
    color = cfg.get("color", "#2251FF")
    bg = cfg.get("bg", "#EEF2FF")
    description = _DESCRIPTIONS.get(agent_id, "")

    targets = get_targets(agent_id)
    n_targets = len(targets)

    agent_runs = [r for r in run_index if r.get("agent_id") == agent_id]
    n_runs = len(agent_runs)
    n_reflections = len(get_apply_history())

    # Prompt + skill versions from latest run
    prompt_version = "v1"
    skill_version = "v1"
    n_eval_cases = "—"
    if agent_runs:
        latest = sorted(agent_runs, key=lambda r: r.get("started_at") or "", reverse=True)[0]
        pv = latest.get("prompt_version")
        if pv is not None:
            prompt_version = f"v{pv}"
        sv = latest.get("skill_version")
        if sv is not None:
            skill_version = f"v{int(sv)}" if isinstance(sv, (int, float)) or (isinstance(sv, str) and sv.isdigit()) else "v1"
        nc = latest.get("n_cases")
        if nc:
            n_eval_cases = str(nc)

    # SVG icons
    target_icon = ic("target", size=13, color="#94A3B8")
    layers_icon = ic("layers", size=13, color="#94A3B8")
    refresh_icon = ic("refresh-cw", size=13, color="#94A3B8")
    agent_icon = ic(icon_name, size=22, color=color)   # SVG Lucide icon — matches agent selector

    def meta_item(icon_html: str, text: str) -> str:
        return (
            f'<span style="display:inline-flex;align-items:center;gap:5px;'
            f'color:#64748B;font-size:12px;">'
            f'{icon_html}<span>{text}</span></span>'
        )

    st.markdown(
        f"""
        <div class="card" style="padding:20px 24px;margin-bottom:12px;">
          <div style="display:flex;align-items:flex-start;gap:16px;">
            <!-- Agent icon -->
            <div style="
                width:48px;height:48px;border-radius:14px;
                background:{bg};
                display:flex;align-items:center;justify-content:center;
                flex-shrink:0;border:1.5px solid {color}22;
            ">{agent_icon}</div>
            <!-- Content -->
            <div style="flex:1;min-width:0;">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                <h2 style="font-size:18px;font-weight:800;color:#0F172A;margin:0;
                           letter-spacing:-0.02em;">{label} — {cfg.get("subtitle", "Agent")}</h2>
              </div>
              <p style="font-size:13.5px;color:#475569;margin:0 0 14px 0;
                        line-height:1.6;max-width:720px;">
                {description}
              </p>
              <!-- Metadata row with icons -->
              <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:center;">
                {meta_item(target_icon, f"{n_targets} customer × product targets")}
                {meta_item(layers_icon, f"Prompt {prompt_version} · Skill {skill_version} · {n_eval_cases} eval cases")}
                {meta_item(refresh_icon, f"{n_runs} run{'s' if n_runs != 1 else ''} · {n_reflections} reflection{'s' if n_reflections != 1 else ''} applied")}
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
