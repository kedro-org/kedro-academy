"""Summarizer Agent for multi-agent PPT generation pipeline.

This module contains the SummarizerAgent class and related helper
functions for generating slide summaries.
"""
from __future__ import annotations

import asyncio
import logging

from ppt_autogen_workflow.base import BaseAgent, SummaryOutput

logger = logging.getLogger(__name__)


class SummarizerAgent(BaseAgent["SummarizerAgent"]):
    """Agent responsible for generating slide summaries.

    Usage:
        agent = SummarizerAgent(llm_context).compile()
        output = await agent.invoke(content_to_summarize)
    """

    agent_name = "SummarizerAgent"
    system_prompt_key = "summarizer_system_prompt"

    async def invoke(self, content_to_summarize: str) -> SummaryOutput:
        """Invoke the summarizer agent to create slide summaries.

        Returns:
            SummaryOutput with summary_text and status
        """
        return await self._run_with_output(content_to_summarize, SummaryOutput)


def generate_summary(
    summarizer_agent: SummarizerAgent, query: str, slide_key: str, instruction: str
) -> str:
    """Generate summary using summarizer agent with structured output.

    Args:
        summarizer_agent: Compiled summarizer agent
        query: Formatted query for summary generation
        slide_key: Unique identifier for the slide
        instruction: Summary instruction for fallback

    Returns:
        Generated summary text
    """
    try:
        summary_output: SummaryOutput = asyncio.run(summarizer_agent.invoke(query))
        summary_text = summary_output.summary_text

        if summary_text:
            return summary_text

        # Fallback
        logger.warning(f"Summary not generated for {slide_key}, using fallback")
        return _create_fallback_summary(slide_key, instruction)

    except Exception as e:
        logger.error(f"Error generating summary for {slide_key}: {str(e)}")
        return _create_fallback_summary(slide_key, instruction)


def _create_fallback_summary(slide_key: str, instruction: str = "") -> str:
    """Create fallback summary when agent fails."""
    if instruction:
        return f"• Analysis for {slide_key}\n• Data insights based on: {instruction[:100]}..."
    return f"• Analysis for {slide_key}\n• Data insights generated"
