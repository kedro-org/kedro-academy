"""Scout models shared across all agents."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Confidence = Literal["high", "medium", "low"]


class Signal(BaseModel):
    """One signal record emitted by a Pattern Scout.

    Written to ``data/<agent_id>/outputs/runs/<run_id>/signals.json`` (per run)
    and appended to ``data/outputs/signal_index.json`` (rolling cross-run index).
    """

    signal_type: str
    agent_id: str
    run_id: str
    confidence: Confidence
    evidence_text: str
    reason: str
    created_at: str
