"""RunIndexEntry — one record per pipeline run, accumulated across pipelines.

Written by RunIndexHook (hooks.py) as an append/upsert into
data/outputs/run_index.json.

NoSQL migration path:
  - run_id       → primary key / document ID
  - agent_id     → partition key (DynamoDB) / shard key (MongoDB)
  - started_at   → sort key / range index
  - Flat dict fields → MongoDB $set / DynamoDB UpdateItem with no schema changes
  - prompt_snapshot / skill_snapshot → move to blob store (S3 URL) in production;
    inline here is fine for the POC scale (3 agents, JSON on disk)
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class RunIndexEntry(BaseModel):
    """Self-contained audit record for one agent run.

    Built up across four pipelines via upsert:
      campaign   → identity, config snapshot, run stats
      evaluation → quality scores, Langfuse links
      scouts     → signal summary
      reflection → reflection_id
      apply      → reflection_applied, applied_at, applied_by
    """

    # ── Identity ────────────────────────────────────────────────────────────
    run_id: str
    agent_id: str
    run_seq: int                         # ordinal for this agent: 1, 2, 3 …

    # ── Timing ──────────────────────────────────────────────────────────────
    started_at: str                      # ISO-8601 UTC
    finished_at: str
    duration_seconds: float
    status: Literal["completed", "partial", "failed"] = "completed"

    # ── Config snapshot (exact inputs — survives apply/reset) ────────────────
    model_name: str
    prompt_name: str                     # e.g. "b2b_sales-system-prompt"
    prompt_version: Optional[int] = None
    prompt_snapshot: str                 # full system prompt text used
    skill_version: Optional[int] = None
    skill_snapshot: str                  # full skill file content used
    judge_model_name: Optional[str] = None
    judge_prompt_version: Optional[int] = None

    # ── Run stats ────────────────────────────────────────────────────────────
    n_cases: int
    n_outputs: int
    n_errors: int

    # ── Quality scores (evaluation pipeline) ─────────────────────────────────
    pass_rate: Optional[float] = None
    mean_score: Optional[float] = None
    mean_per_scorer: Optional[dict[str, float]] = None
    passing_threshold: Optional[float] = None
    langfuse_experiment_url: Optional[str] = None
    langfuse_dataset_run_id: Optional[str] = None

    # ── Signals (scouts pipeline) ─────────────────────────────────────────────
    n_signals: Optional[int] = None
    signal_types: Optional[list[str]] = None
    signals_by_confidence: Optional[dict[str, int]] = None

    # ── Reflection + Apply lineage ────────────────────────────────────────────
    reflection_id: Optional[str] = None
    reflection_applied: bool = False
    applied_at: Optional[str] = None
    applied_by: Optional[str] = None     # reviewer name (populated by apply step)

    # ── Delta vs previous run (same agent) ───────────────────────────────────
    prev_run_id: Optional[str] = None
    delta_mean_score: Optional[float] = None   # positive = improvement
    delta_pass_rate: Optional[float] = None
