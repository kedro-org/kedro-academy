"""Kedro nodes for single-agent AutoGen PPT generation pipeline."""
from __future__ import annotations

import logging
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from .agent import PPTGenerationAgent
from ppt_autogen_workflow.base import ChartOutput, SummaryOutput

logger = logging.getLogger(__name__)


def run_ppt_agent(
    llm_context: LLMContext,
    sa_slide_configs: dict[str, Any],
) -> dict[str, Any]:
    """Run PPT agent to generate charts and summaries.

    This is the agentic node that uses the LLM to generate content.
    
    Args:
        llm_context: LLMContext containing llm, prompts, and tools
        sa_slide_configs: Pre-parsed slide configurations from preprocessing

    Returns:
        Dict mapping slide_key to content dict with slide_title, chart_path, summary
    """
    import asyncio

    try:
        # Create the PPT agent directly from LLMContext
        agent = PPTGenerationAgent(llm_context).compile()

        # Extract slides from unified format
        slides = sa_slide_configs.get('slides', {})

        # Generate charts and summaries for each slide
        slide_content = {}

        for slide_key, config in slides.items():
            # Generate chart with focused query
            chart_instruction = config.get('chart_instruction', '')
            chart_query = (
                f"For slide '{config['slide_title']}', create a chart.\n\n"
                f"Chart Instruction: {chart_instruction}\n\n"
                f"Call the generate_chart tool with the instruction above to create the chart."
            )
            chart_output: ChartOutput = asyncio.run(agent.invoke_for_chart(chart_query))
            chart_path = chart_output.chart_path if chart_output.chart_path else ""

            # Generate summary with focused query (separate from chart)
            summary_instruction = config.get('summary_instruction', '')
            summary_query = (
                f"For slide '{config['slide_title']}', create a summary.\n\n"
                f"Summary Instruction: {summary_instruction}\n\n"
                f"Call the generate_summary tool with the instruction above to generate the summary."
            )
            summary_output: SummaryOutput = asyncio.run(agent.invoke_for_summary(summary_query))
            summary_text = summary_output.summary_text if summary_output.summary_text else ""

            # Bundle content for assembly
            slide_content[slide_key] = {
                'slide_title': config['slide_title'],
                'chart_path': chart_path,
                'summary': summary_text,
            }

        return slide_content

    except Exception as e:
        logger.error(f"PPT agent execution failed: {str(e)}", exc_info=True)
        raise
