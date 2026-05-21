"""Apply pipeline models."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AppliedMarker(BaseModel):
    proposal_id: str
    applied_at: str
    prompt_version: str
    skill_hash: str
    new_eval_case_ids: list[str] = Field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
