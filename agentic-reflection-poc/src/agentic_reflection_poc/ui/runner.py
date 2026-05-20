"""Streamlit subprocess helper for Kedro pipelines."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Callable

LogCallback = Callable[[str], None] | None


def _kedro_command() -> list[str]:
    kedro = shutil.which("kedro")
    if kedro:
        return [kedro]
    return [sys.executable, "-m", "kedro"]


def run_pipeline(
    pipeline_name: str,
    params: dict[str, str] | None = None,
    on_log: LogCallback = None,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = _kedro_command() + ["run", "--pipelines", pipeline_name]
    if params:
        param_str = ",".join(f"{k}={v}" for k, v in params.items())
        cmd.extend(["--params", param_str])

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd,
    )
    output_lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        output_lines.append(line)
        if on_log:
            on_log(line)
    process.wait()
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=process.returncode,
        stdout="".join(output_lines),
        stderr="",
    )
