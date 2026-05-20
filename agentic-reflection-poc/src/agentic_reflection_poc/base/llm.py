"""LLM invocation helpers for Kedro LLMContext nodes."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from kedro.pipeline.llm_context import LLMContext
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from agentic_reflection_poc.utils.prompt_utils import prompt_text

T = TypeVar("T", bound=BaseModel)


def invoke_text(
    context: LLMContext,
    user: str,
    *,
    system_key: str = "campaign_system_prompt",
    extra_system: str = "",
) -> str:
    system = prompt_text(context.prompts.get(system_key, ""))
    if extra_system:
        system = f"{system}\n{extra_system}"
    if context.llm is None:
        raise RuntimeError("LLM context has no model loaded — check conf/base/parameters.yml.")
    response = context.llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return str(response.content or "")


def invoke_json(
    context: LLMContext,
    user: str,
    schema: type[T],
    *,
    system_key: str = "judge_system_prompt",
) -> T:
    raw = invoke_text(
        context,
        user,
        system_key=system_key,
        extra_system="Respond with valid JSON only. No markdown fences.",
    )
    return schema.model_validate(_extract_json(raw))


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)
