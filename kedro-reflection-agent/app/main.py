"""Streamlit dashboard entry point for the B2B Campaign Agent — Reflection Demo.

Run with:  streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.state import (  # noqa: E402
    load_demo_state,
    reset_demo_state,
    save_demo_state,
    transition,
)
from app import ui_components as components  # noqa: E402
from app.runner import run_pipeline  # noqa: E402
from app.components.step_1_run import render_step1  # noqa: E402
from app.components.step_2_reflect import render_step2  # noqa: E402
from app.components.step_3_rerun import render_step3  # noqa: E402

_KEDRO_AVATAR = "https://avatars.githubusercontent.com/kedro-org"

st.set_page_config(
    page_title="B2B Campaign Agent — Reflection Demo",
    page_icon=_KEDRO_AVATAR,
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={},
)

PROPOSAL_ID = "proposal_1"
STATE_PATH = ROOT / "data" / "demo_state.json"


# ── path helpers ──────────────────────────────────────────────────────────────

def artifact(run_id: str, filename: str) -> Path:
    return ROOT / "data" / "outputs" / "runs" / run_id / filename


def reporting(run_id: str, filename: str) -> Path:
    return ROOT / "data" / "outputs" / "runs" / run_id / filename


def pipeline_params(extra: dict[str, str]) -> dict[str, str]:
    return extra


# ── pipeline runner with live log streaming ───────────────────────────────────

def run_with_logs(
    pipeline_name: str,
    params: dict[str, str],
    log_target: st.delta_generator.DeltaGenerator,
    log_key: str,
) -> bool:
    lines: list[str] = st.session_state.setdefault(log_key, [])

    def on_log(line: str) -> None:
        lines.append(line)
        components.update_pipeline_log(log_target, lines)

    result = run_pipeline(
        pipeline_name,
        params=params,
        on_log=on_log,
        cwd=str(ROOT),
    )

    components.update_pipeline_log(log_target, lines)

    if result.returncode != 0:
        st.error(f"Pipeline `{pipeline_name}` failed (exit {result.returncode}). See logs above.")
        return False
    return True


# ── load state ────────────────────────────────────────────────────────────────

demo = load_demo_state(STATE_PATH)


def _do_reset() -> None:
    import shutil
    import yaml as _yaml
    from kedro_reflection_agent.utils.prompt_utils import SEED_PROMPT as _SEED_PROMPT, SEED_SKILL as _SEED_SKILL
    outputs_dir = ROOT / "data" / "outputs"
    if outputs_dir.exists():
        shutil.rmtree(outputs_dir)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        (outputs_dir / "runs").mkdir(exist_ok=True)
        (outputs_dir / "reflections").mkdir(exist_ok=True)
    prompt_path = ROOT / "data" / "agent_run" / "prompts" / "campaign_agent_system_prompt.yaml"
    prompt_path.write_text(_yaml.safe_dump(_SEED_PROMPT, sort_keys=False), encoding="utf-8")
    (ROOT / "data" / "agent_run" / "skills" / "b2b-email-style.md").write_text(_SEED_SKILL, encoding="utf-8")
    reset_demo_state(STATE_PATH)
    st.rerun()


# ── page chrome + header ──────────────────────────────────────────────────────

components.inject_global_css()
components.inject_page_chrome(kedro_avatar_url=_KEDRO_AVATAR)

_hcol, _rcol = st.columns([11, 1])
with _hcol:
    components.page_header(kedro_avatar_url=_KEDRO_AVATAR)
with _rcol:
    st.markdown('<div style="padding-top:26px;display:flex;justify-content:flex-end;">', unsafe_allow_html=True)
    if st.button("Reset", key="reset_top", help="Clears all run data and restores v1 prompt"):
        _do_reset()
    st.markdown("</div>", unsafe_allow_html=True)

step_num = {"idle": 0, "run_1_done": 1, "reflected": 1, "applied": 2, "run_2_done": 3}
components.workflow_bar(step_num.get(demo.state, 0))

proposal_path = ROOT / "data" / "outputs" / "reflections" / PROPOSAL_ID

# ── step 1 ────────────────────────────────────────────────────────────────────

render_step1(
    demo=demo,
    root=ROOT,
    artifact=artifact,
    reporting=reporting,
    pipeline_params=pipeline_params,
    run_with_logs=run_with_logs,
    on_complete=lambda: (
        save_demo_state(
            transition(demo, "run_1_done", run_1_id="run_1"),
            STATE_PATH,
        )
    ),
)

st.divider()

# ── step 2 ────────────────────────────────────────────────────────────────────

render_step2(
    demo=demo,
    root=ROOT,
    proposal_id=PROPOSAL_ID,
    proposal_path=proposal_path,
    reporting=reporting,
    pipeline_params=pipeline_params,
    run_with_logs=run_with_logs,
    on_reflect=lambda: (
        save_demo_state(
            transition(demo, "reflected", proposal_id=PROPOSAL_ID),
            STATE_PATH,
        )
    ),
    on_apply=lambda: (
        save_demo_state(
            transition(demo, "applied", applied_id=PROPOSAL_ID),
            STATE_PATH,
        )
    ),
)

st.divider()

# ── step 3 ────────────────────────────────────────────────────────────────────

render_step3(
    demo=demo,
    root=ROOT,
    proposal_path=proposal_path,
    artifact=artifact,
    reporting=reporting,
    pipeline_params=pipeline_params,
    run_with_logs=run_with_logs,
    on_complete=lambda: (
        save_demo_state(
            transition(demo, "run_2_done", run_2_id="run_2"),
            STATE_PATH,
        )
    ),
)
