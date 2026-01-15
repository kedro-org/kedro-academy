"""Kedro nodes for single-agent AutoGen PPT generation pipeline."""
from __future__ import annotations

import logging
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from .agent import PPTGenerationAgent
from .utils import format_sa_prompts
from ppt_autogen_workflow.base import ChartOutput, SummaryOutput
from ppt_autogen_workflow.base.preprocessing import parse_slide_requirements

logger = logging.getLogger(__name__)


def parse_sa_slide_requirements(
    slide_generation_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Parse slide generation requirements for SA pipeline.

    Args:
        slide_generation_requirements: Raw slide configuration from YAML

    Returns:
        Dictionary with SA slide configurations:
        - slides: Unified slide configurations for single agent
    """
    return parse_slide_requirements(slide_generation_requirements, pipeline_type="sa")


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

        # Get user prompt template and format prompts for each slide
        user_prompt_template = llm_context.prompts.get("ppt_generator_user_prompt")
        slides = sa_slide_configs.get('slides', {})
        formatted_prompts = format_sa_prompts(slides, user_prompt_template)

        # Generate charts and summaries for each slide
        slide_content = {}

        for slide_key, config in slides.items():
            user_prompt = formatted_prompts.get(slide_key, '')

            # Generate chart - agent uses generate_chart tool with instruction
            # Agent analyzes instruction and generates chart from data
            chart_query = f"{user_prompt}\n\nTask: Generate a chart using the generate_chart tool. Provide the chart instruction from the slide config and let the tool analyze the data and create the chart."
            chart_output: ChartOutput = asyncio.run(agent.invoke_for_chart(chart_query))
            chart_path = chart_output.chart_path if chart_output.chart_path else ""

            # Generate summary - agent uses generate_summary tool with instruction
            # Agent analyzes instruction and generates insights from data
            summary_query = f"{user_prompt}\n\nTask: Generate a summary using the generate_summary tool. Provide the summary instruction from the slide config and let the tool analyze the data and generate insights."
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
