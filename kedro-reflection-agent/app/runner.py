"""Subprocess wrapper around `kedro run`.

The Streamlit dashboard invokes Kedro pipelines through this module so the UI
never imports Kedro directly. Pipelines write their artifacts to ``data/`` and
the dashboard reads them back from disk.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

LogCallback = Callable[[str], None] | None

PROJECT_ROOT = Path(__file__).parent.parent


def _kedro_cmd() -> list[str]:
    kedro = shutil.which("kedro")
    if kedro:
        return [kedro]
    return [sys.executable, "-m", "kedro"]


def _run_pipeline(
    pipeline: str,
    params: dict[str, str],
    on_log: LogCallback = None,
) -> subprocess.CompletedProcess[str]:
    cmd = _kedro_cmd() + ["run", "--pipelines", pipeline]
    if params:
        params_str = ",".join(f"{k}={v}" for k, v in params.items())
        cmd += ["--params", params_str]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=PROJECT_ROOT,
    )
    lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        lines.append(line)
        if on_log:
            on_log(line)
    process.wait()
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=process.returncode,
        stdout="".join(lines),
        stderr="",
    )


def run_campaign(
    run_id: str,
    on_log: LogCallback = None,
) -> tuple[bool, str]:
    """Run campaign then evaluation for *run_id*, streaming lines via on_log."""
    logs: list[str] = []

    def _log(line: str) -> None:
        logs.append(line)
        if on_log:
            on_log(line)

    r = _run_pipeline("campaign", {"run_id": run_id}, on_log=_log)
    if r.returncode != 0:
        return False, "".join(logs)

    r = _run_pipeline("evaluation", {"run_id": run_id}, on_log=_log)
    return r.returncode == 0, "".join(logs)


def run_reflection(
    run_id: str,
    reflection_id: str,
    on_log: LogCallback = None,
) -> tuple[bool, str]:
    logs: list[str] = []

    def _log(line: str) -> None:
        logs.append(line)
        if on_log:
            on_log(line)

    r = _run_pipeline(
        "reflection",
        {"run_id": run_id, "reflection_id": reflection_id},
        on_log=_log,
    )
    return r.returncode == 0, "".join(logs)


def run_apply(
    reflection_id: str,
    on_log: LogCallback = None,
) -> tuple[bool, str]:
    logs: list[str] = []

    def _log(line: str) -> None:
        logs.append(line)
        if on_log:
            on_log(line)

    r = _run_pipeline("apply", {"reflection_id": reflection_id}, on_log=_log)
    return r.returncode == 0, "".join(logs)
