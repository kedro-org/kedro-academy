"""Chart Generator Agent for multi-agent PPT generation pipeline.

This module contains the ChartGeneratorAgent class and related helper
functions for generating data visualizations.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent, ChartOutput

logger = logging.getLogger(__name__)


class ChartGeneratorAgent(BaseAgent["ChartGeneratorAgent"]):
    """Agent responsible for generating data visualizations."""

    async def invoke(self, chart_requirements: str) -> ChartOutput:
        """Invoke the chart generator agent to create charts.

        Returns:
            ChartOutput with chart_path and status
        """
        return await self._run_with_output(chart_requirements, ChartOutput)


def create_chart_generator_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> ChartGeneratorAgent:
    """Create a chart generator agent for data visualization."""
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="ChartGeneratorAgent",
    )
    return ChartGeneratorAgent(context).compile()


def generate_chart(
    chart_agent: ChartGeneratorAgent, query: str, slide_key: str, instruction: str
) -> str:
    """Generate chart using chart agent with structured output.

    Args:
        chart_agent: Compiled chart generator agent
        query: Formatted query for chart generation
        slide_key: Unique identifier for the slide
        instruction: Chart instruction for fallback

    Returns:
        Path to the generated chart image
    """
    try:
        chart_output: ChartOutput = asyncio.run(chart_agent.invoke(query))
        chart_path = chart_output.chart_path

        if chart_path and Path(chart_path).exists():
            return chart_path

        # Fallback: create placeholder chart
        logger.warning(f"Chart not generated for {slide_key}, creating placeholder")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"Chart for {slide_key}\n{instruction[:50]}...",
                ha='center', va='center', fontsize=12, wrap=True)
        ax.set_title(f"Chart: {slide_key}")

        temp_dir = Path(tempfile.mkdtemp())
        fallback_path = temp_dir / f"chart_{slide_key}.png"
        fig.savefig(fallback_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        return str(fallback_path)

    except Exception as e:
        logger.error(f"Error generating chart for {slide_key}: {str(e)}")
        return ""
