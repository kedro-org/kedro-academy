"""Subprocess wrapper around `kedro run`.

The Streamlit dashboard invokes Kedro pipelines through this module so the UI
never imports Kedro directly. Pipelines write their artifacts to ``data/`` and
the dashboard reads them back from disk.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def _run_pipeline(pipeline: str, params: dict[str, str]) -> tuple[bool, str]:
    """Run a single Kedro pipeline and return (success, combined log)."""
    cmd = ["kedro", "run", "--pipelines", pipeline]
    if params:
        params_str = ",".join(f"{k}={v}" for k, v in params.items())
        cmd += ["--params", params_str]

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    log = result.stdout + result.stderr
    return result.returncode == 0, log


def run_campaign(run_id: str) -> tuple[bool, str]:
    """Run campaign + evaluation for *run_id*.

    Runs campaign first; evaluation is run separately so each has its own log.
    Returns (success, combined_log).
    """
    logs: list[str] = []

    ok, log = _run_pipeline("campaign", {"run_id": run_id})
    logs.append(log)
    if not ok:
        return False, "".join(logs)

    ok, log = _run_pipeline("evaluation", {"run_id": run_id})
    logs.append(log)
    return ok, "".join(logs)


def run_reflection(run_id: str, reflection_id: str) -> tuple[bool, str]:
    """Run the reflection pipeline."""
    return _run_pipeline(
        "reflection",
        {"run_id": run_id, "reflection_id": reflection_id},
    )


def run_apply(reflection_id: str) -> tuple[bool, str]:
    """Run the apply pipeline to commit the approved reflection."""
    return _run_pipeline("apply", {"reflection_id": reflection_id})
