"""Chart Generator Agent for multi-agent PPT generation pipeline.

This module contains the ChartGeneratorAgent class and related helper
functions for generating data visualizations.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent
from ppt_autogen_workflow.utils.node_helpers import extract_chart_path

logger = logging.getLogger(__name__)


class ChartGeneratorAgent(BaseAgent["ChartGeneratorAgent"]):
    """Agent responsible for generating data visualizations."""

    async def invoke(self, chart_requirements: str) -> dict[str, Any]:
        """Invoke the chart generator agent to create charts."""
        self._ensure_compiled()

        try:
            result = await self._agent.run(task=chart_requirements)
            chart_output = {
                "requirements": chart_requirements,
                "chart_data": self._extract_content_from_response(result, "chart"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }
            return chart_output

        except Exception as e:
            logger.error(f"Chart generator agent failed: {str(e)}")
            return {
                "requirements": chart_requirements,
                "chart_data": {},
                "tools_used": [],
                "success": False,
                "error": str(e),
            }


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
) -> tuple[str, plt.Figure | None]:
    """Generate chart using chart agent.

    Args:
        chart_agent: Compiled chart generator agent
        query: Formatted query for chart generation
        slide_key: Unique identifier for the slide
        instruction: Chart instruction for fallback

    Returns:
        Tuple of (chart_path, matplotlib_figure)
    """
    try:
        chart_result = asyncio.run(chart_agent.invoke(query))
        chart_path = extract_chart_path(chart_result)

        if chart_path and Path(chart_path).exists():
            try:
                from matplotlib.image import imread
                img = imread(chart_path)
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.imshow(img)
                ax.axis('off')
                return str(chart_path), fig
            except Exception as e:
                logger.warning(f"Could not load chart image: {e}")

        # Fallback: create placeholder chart
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"Chart for {slide_key}\n{instruction[:50]}...",
                ha='center', va='center', fontsize=12, wrap=True)
        ax.set_title(f"Chart: {slide_key}")

        temp_dir = Path(tempfile.mkdtemp())
        chart_path = temp_dir / f"chart_{slide_key}.png"
        fig.savefig(chart_path, dpi=300, bbox_inches='tight')
        return str(chart_path), fig

    except Exception as e:
        logger.error(f"Error generating chart for {slide_key}: {str(e)}")
        return "", None
