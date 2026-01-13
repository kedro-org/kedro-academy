"""Summarizer Agent for multi-agent PPT generation pipeline.

This module contains the SummarizerAgent class and related helper
functions for generating slide summaries.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent
from ppt_autogen_workflow.utils.node_helpers import (
    extract_summary_text,
    create_fallback_summary,
)

logger = logging.getLogger(__name__)


class SummarizerAgent(BaseAgent["SummarizerAgent"]):
    """Agent responsible for generating slide summaries."""

    async def invoke(self, content_to_summarize: str) -> dict[str, Any]:
        """Invoke the summarizer agent to create slide summaries."""
        self._ensure_compiled()

        try:
            result = await self._agent.run(task=content_to_summarize)
            summary_output = {
                "original_content": content_to_summarize,
                "summary": self._extract_content_from_response(result, "summary"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }
            return summary_output

        except Exception as e:
            logger.error(f"Summarizer agent failed: {str(e)}")
            return {
                "original_content": content_to_summarize,
                "summary": {},
                "tools_used": [],
                "success": False,
                "error": str(e),
            }


def create_summarizer_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> SummarizerAgent:
    """Create a summarizer agent for slide content creation."""
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="SummarizerAgent",
    )
    return SummarizerAgent(context).compile()


def generate_summary(
    summarizer_agent: SummarizerAgent, query: str, slide_key: str, instruction: str
) -> str:
    """Generate summary using summarizer agent.

    Args:
        summarizer_agent: Compiled summarizer agent
        query: Formatted query for summary generation
        slide_key: Unique identifier for the slide
        instruction: Summary instruction for fallback

    Returns:
        Generated summary text
    """
    try:
        summary_result = asyncio.run(summarizer_agent.invoke(query))
        summary_text = extract_summary_text(summary_result)
        return summary_text if summary_text else create_fallback_summary(slide_key, instruction)
    except Exception as e:
        logger.error(f"Error generating summary for {slide_key}: {str(e)}")
        return create_fallback_summary(slide_key, instruction)
