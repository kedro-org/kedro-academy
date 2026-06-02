"""Subprocess wrapper around `kedro run`.

The Streamlit dashboard invokes Kedro pipelines through this module so the UI
never imports Kedro directly. Pipelines write their artifacts to ``data/`` and
the dashboard reads them back from disk.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

LogCallback = Callable[[str], None] | None

PROJECT_ROOT = Path(__file__).parent.parent
_DATA = PROJECT_ROOT / "data"


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


# ── Pipeline runners ──────────────────────────────────────────────────────────

def run_campaign(
    run_id: str,
    agent_id: str,
    on_log: LogCallback = None,
) -> tuple[bool, str]:
    """Run campaign then evaluation for *agent_id*/*run_id*."""
    logs: list[str] = []

    def _log(line: str) -> None:
        logs.append(line)
        if on_log:
            on_log(line)

    r = _run_pipeline("campaign", {"agent_id": agent_id, "run_id": run_id}, on_log=_log)
    if r.returncode != 0:
        return False, "".join(logs)

    r = _run_pipeline("evaluation", {"agent_id": agent_id, "run_id": run_id}, on_log=_log)
    return r.returncode == 0, "".join(logs)


def run_scouts(
    run_id: str,
    agent_id: str,
    on_log: LogCallback = None,
) -> tuple[bool, str]:
    """Run scouts for *agent_id*/*run_id*."""
    logs: list[str] = []

    def _log(line: str) -> None:
        logs.append(line)
        if on_log:
            on_log(line)

    r = _run_pipeline("scouts", {"agent_id": agent_id, "run_id": run_id}, on_log=_log)
    return r.returncode == 0, "".join(logs)


def run_reflection(
    run_id: str,
    reflection_id: str,
    agent_id: str,
    on_log: LogCallback = None,
) -> tuple[bool, str]:
    logs: list[str] = []

    def _log(line: str) -> None:
        logs.append(line)
        if on_log:
            on_log(line)

    r = _run_pipeline(
        "reflection",
        {"agent_id": agent_id, "run_id": run_id, "reflection_id": reflection_id},
        on_log=_log,
    )
    return r.returncode == 0, "".join(logs)


def run_apply(
    reflection_id: str,
    agent_id: str,
    on_log: LogCallback = None,
) -> tuple[bool, str]:
    logs: list[str] = []

    def _log(line: str) -> None:
        logs.append(line)
        if on_log:
            on_log(line)

    r = _run_pipeline(
        "apply",
        {"agent_id": agent_id, "reflection_id": reflection_id},
        on_log=_log,
    )
    return r.returncode == 0, "".join(logs)


# ── Reset helpers ─────────────────────────────────────────────────────────────

def reset_run(run_id: str, agent_id: str) -> None:
    """Delete campaign+eval outputs and remove the run from run_index."""
    run_dir = _DATA / agent_id / "outputs" / "runs" / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / ".gitkeep").touch()

    _remove_from_json(
        _DATA / "outputs" / "run_index.json",
        lambda r: not (r.get("run_id") == run_id and r.get("agent_id") == agent_id),
    )


def reset_scouts(run_id: str, agent_id: str) -> None:
    """Delete signals for a run and remove entries from signal_index."""
    signals_file = _DATA / agent_id / "outputs" / "runs" / run_id / "signals.json"
    if signals_file.exists():
        signals_file.unlink()

    _remove_from_json(
        _DATA / "outputs" / "signal_index.json",
        lambda e: not (e.get("run_id") == run_id and e.get("agent_id") == agent_id),
    )


def reset_reflection(reflection_id: str, agent_id: str) -> None:
    """Delete reflection artifacts."""
    refl_dir = _DATA / agent_id / "outputs" / "reflections" / reflection_id
    if refl_dir.exists():
        shutil.rmtree(refl_dir)
        refl_dir.mkdir(parents=True, exist_ok=True)
        (refl_dir / ".gitkeep").touch()


def reset_apply(reflection_id: str, agent_id: str) -> None:
    """Remove an apply entry so the approval gate becomes active again."""
    _remove_from_json(
        _DATA / "outputs" / "apply_history.json",
        lambda h: not (h.get("reflection_id") == reflection_id and h.get("agent_id") == agent_id),
    )


def _remove_from_json(path: Path, keep: Callable[[dict], bool]) -> None:
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            path.write_text(json.dumps([x for x in data if keep(x)], indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
