"""Chart Generator Agent for multi-agent PPT generation pipeline.

This module contains the ChartGeneratorAgent class and related helper
functions for generating data visualizations.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ppt_autogen_workflow.base import BaseAgent, ChartOutput

logger = logging.getLogger(__name__)


class ChartGenerationError(Exception):
    """Raised when chart generation fails."""
    pass


class ChartGeneratorAgent(BaseAgent["ChartGeneratorAgent"]):
    """Agent responsible for generating data visualizations.

    Usage:
        agent = ChartGeneratorAgent(llm_context).compile()
        output = await agent.invoke(chart_requirements)
    """

    agent_name = "ChartGeneratorAgent"
    system_prompt_key = "chart_generator_system_prompt"

    async def invoke(self, chart_requirements: str) -> ChartOutput:
        """Invoke the chart generator agent to create charts.

        Returns:
            ChartOutput with chart_path and status
        """
        return await self._run_with_output(chart_requirements, ChartOutput)


def generate_chart(
    chart_agent: ChartGeneratorAgent, query: str, slide_key: str, instruction: str
) -> str:
    """Generate chart using chart agent with structured output.

    Args:
        chart_agent: Compiled chart generator agent
        query: Formatted query for chart generation
        slide_key: Unique identifier for the slide
        instruction: Chart instruction (for error context)

    Returns:
        Path to the generated chart image

    Raises:
        ChartGenerationError: If chart generation fails or produces invalid output
    """
    try:
        chart_output: ChartOutput = asyncio.run(chart_agent.invoke(query))
        chart_path = chart_output.chart_path

        if chart_path and Path(chart_path).exists():
            return chart_path

        # Chart generation failed - raise error instead of silent fallback
        raise ChartGenerationError(
            f"Chart generation for '{slide_key}' did not produce a valid file. "
            f"Instruction: {instruction[:100]}..."
        )

    except ChartGenerationError:
        raise
    except Exception as e:
        logger.error(f"Error generating chart for {slide_key}: {str(e)}")
        raise ChartGenerationError(
            f"Chart generation failed for '{slide_key}': {str(e)}"
        ) from e
