"""Shared helpers used by all step components."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

_SCOREBOARD_COLUMNS = [
    "case_id",
    "company_name",
    "product_name",
    "total_score",
    "failure_tags",
]


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _case_scores_dataframe(case_scores: list[dict[str, Any]]) -> pd.DataFrame:
    if not case_scores:
        return pd.DataFrame(columns=_SCOREBOARD_COLUMNS)
    df = pd.DataFrame(case_scores)
    for col in _SCOREBOARD_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[_SCOREBOARD_COLUMNS]


def _render_pipeline_logs(session_key: str) -> None:
    lines = st.session_state.get(session_key) or []
    if lines:
        st.code("".join(lines[-200:]), language="log")
    else:
        st.caption("Pipeline logs appear here after you run a step.")
