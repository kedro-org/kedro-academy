"""Start and monitor Kedro-Viz as a background process for the Streamlit app."""

from __future__ import annotations

import logging
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

import streamlit as st

logger = logging.getLogger(__name__)

KEDRO_VIZ_HOST = "127.0.0.1"
KEDRO_VIZ_PORT = 4141
KEDRO_VIZ_BASE = f"http://{KEDRO_VIZ_HOST}:{KEDRO_VIZ_PORT}"

VizStatus = Literal["ready", "starting", "failed", "unavailable"]


def kedro_viz_url(*, pipeline_id: str | None = None) -> str:
    """Build Kedro-Viz URL with optional pipeline pre-selection via `pid` query param."""
    if not pipeline_id:
        return KEDRO_VIZ_BASE
    return f"{KEDRO_VIZ_BASE}?{urlencode({'pid': pipeline_id})}"


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _kedro_cmd() -> list[str]:
    kedro = shutil.which("kedro")
    if kedro:
        return [kedro]
    return [sys.executable, "-m", "kedro"]


def ensure_kedro_viz_running(project_root: str | Path) -> VizStatus:
    """Ensure Kedro-Viz is listening on 4141; start a background process if needed."""
    if _port_open(KEDRO_VIZ_HOST, KEDRO_VIZ_PORT):
        return "ready"

    proc: subprocess.Popen[str] | None = st.session_state.get("kedro_viz_proc")
    if proc is not None and proc.poll() is None:
        for _ in range(12):
            if _port_open(KEDRO_VIZ_HOST, KEDRO_VIZ_PORT):
                return "ready"
            time.sleep(0.25)
        return "starting"

    if st.session_state.get("kedro_viz_start_attempted") and proc is not None and proc.poll() is not None:
        return "failed"

    root = Path(project_root)
    cmd = _kedro_cmd() + [
        "viz",
        "run",
        "--host",
        KEDRO_VIZ_HOST,
        "--port",
        str(KEDRO_VIZ_PORT),
        "--no-browser",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        logger.exception("kedro executable not found")
        return "unavailable"

    st.session_state.kedro_viz_proc = proc
    st.session_state.kedro_viz_start_attempted = True

    for _ in range(20):
        if proc.poll() is not None:
            err = (proc.stderr.read() if proc.stderr else "") or "Kedro-Viz exited early."
            st.session_state.kedro_viz_error = err.strip()[:500]
            return "failed"
        if _port_open(KEDRO_VIZ_HOST, KEDRO_VIZ_PORT):
            return "ready"
        time.sleep(0.3)

    return "starting"
