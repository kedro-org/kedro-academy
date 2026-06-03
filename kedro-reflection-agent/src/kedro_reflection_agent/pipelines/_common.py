"""Helpers shared by more than one pipeline.

Kept deliberately small. Anything pipeline-specific should live in that
pipeline's ``nodes.py``; this module is for things that would otherwise be
copy-pasted across multiple pipelines.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_APPLY_HISTORY_PATH = Path("data/outputs/apply_history.json")


def load_prompt_version(agent_id: str) -> int:
    """Derive prompt version from apply_history: base 1 + number of applies for this agent."""
    try:
        history = json.loads(_APPLY_HISTORY_PATH.read_text(encoding="utf-8"))
        return sum(1 for e in history if e.get("agent_id") == agent_id) + 1
    except (FileNotFoundError, json.JSONDecodeError):
        return 1

from kedro.pipeline import LLMContext
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel


def build_structured_chain(
    context: LLMContext,
    prompt_key: str,
    output_schema: type[BaseModel],
) -> Runnable:
    """Compose ``ChatPromptTemplate | LLM.with_structured_output(schema)``.

    ``mode: langchain`` on ``LangfusePromptDataset`` should give us a
    ``ChatPromptTemplate`` directly. We defensively handle ``ChatPromptClient``
    (Langfuse's raw return type) in case the conversion isn't already applied,
    matching the pattern used in the source-of-truth ``kedro-agentic-workflows``
    project.
    """
    raw_prompt = context.prompts[prompt_key]

    if isinstance(raw_prompt, ChatPromptTemplate):
        chat_prompt = raw_prompt
    elif hasattr(raw_prompt, "get_langchain_prompt"):
        chat_prompt = ChatPromptTemplate.from_messages(raw_prompt.get_langchain_prompt())
    else:
        chat_prompt = ChatPromptTemplate.from_messages(raw_prompt)

    structured_llm = context.llm.with_structured_output(output_schema)
    return chat_prompt | structured_llm


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string (used for ``started_at`` etc.)."""
    return datetime.now(timezone.utc).isoformat()
