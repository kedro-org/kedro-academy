"""Kedro nodes for single-agent AutoGen PPT generation pipeline.

This module contains node functions with clear separation between:
1. parse_requirements - Deterministic data preparation
2. run_ppt_agent - Agentic chart/summary generation
3. assemble_presentation - Deterministic slide assembly
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from .agent import PPTGenerationAgent
from .agent_helpers import (
    generate_chart,
    generate_summary,
    create_error_presentation,
)
# Import shared utilities from MA pipeline
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen.presentation import (
    combine_presentations,
    format_summary_text,
    create_slide,
)
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml

logger = logging.getLogger(__name__)


def parse_requirements(
    slide_generation_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Parse slide generation requirements from YAML.

    This is a deterministic node that prepares slide configurations
    for the agent to process.

    Args:
        slide_generation_requirements: Raw slide configuration from YAML

    Returns:
        Parsed slide configurations with structured format
    """
    slide_definitions = parse_instructions_yaml(slide_generation_requirements)
    data_context = "Sales data available through agent tools"

    slides = {}
    for slide_key, slide_config in slide_definitions.items():
        objective = slide_config.get('objective', {})
        slides[slide_key] = {
            'slide_title': objective.get('slide_title', slide_key),
            'chart_instruction': objective.get('chart_instruction', ''),
            'summary_instruction': objective.get('summary_instruction', ''),
            'data_context': data_context,
        }

    return {'slides': slides}


def run_ppt_agent(
    llm_context: LLMContext,
    slide_configs: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    """Run PPT agent to generate charts and summaries.

    This is the agentic node that uses the LLM to generate content.
    It receives parsed requirements and outputs raw chart paths, summaries,
    and combined slide content for assembly.

    Args:
        llm_context: LLMContext containing llm, prompts, and tools
        slide_configs: Parsed slide configurations from parse_requirements

    Returns:
        Tuple of (slide_chart_paths, slide_summaries, slide_content)
        where slide_content bundles everything needed for assembly
    """
    try:
        # Create the PPT agent directly from LLMContext
        agent = PPTGenerationAgent(llm_context).compile()

        # Get user prompt template for formatting
        user_prompt_template = llm_context.prompts.get("ppt_generator_user_prompt")

        # Format user prompts for each slide
        slides = slide_configs.get('slides', {})
        formatted_prompts = {}

        for slide_key, config in slides.items():
            slide_config_str = (
                f"Slide Title: {config['slide_title']}\n"
                f"Chart Instruction: {config['chart_instruction']}\n"
                f"Summary Instruction: {config['summary_instruction']}\n"
                f"Data Context: {config['data_context']}"
            )
            if hasattr(user_prompt_template, 'format'):
                formatted_prompt = user_prompt_template.format(slide_config=slide_config_str)
            else:
                formatted_prompt = str(user_prompt_template).replace("{slide_config}", slide_config_str)
            formatted_prompts[slide_key] = formatted_prompt

        # Generate charts and summaries for each slide
        slide_chart_paths = {}
        slide_summaries = {}
        slide_content = {}

        for slide_key, config in slides.items():
            user_prompt = formatted_prompts.get(slide_key, '')

            # Generate chart
            chart_path = generate_chart(
                agent, user_prompt, slide_key, config.get('chart_instruction', '')
            )
            slide_chart_paths[slide_key] = chart_path

            # Generate summary
            summary_text = generate_summary(
                agent, user_prompt, slide_key, chart_path
            )
            formatted_summary = format_summary_text(summary_text)
            slide_summaries[slide_key] = formatted_summary

            # Bundle content for assembly
            slide_content[slide_key] = {
                'slide_title': config['slide_title'],
                'chart_path': chart_path,
                'summary': formatted_summary,
            }

        return slide_chart_paths, slide_summaries, slide_content

    except Exception as e:
        logger.error(f"PPT agent execution failed: {str(e)}", exc_info=True)
        raise


def assemble_presentation(
    slide_content: dict[str, Any],
) -> Any:
    """Assemble final presentation from generated slide content.

    This is a deterministic node that creates slides from the agent-generated content.

    Args:
        slide_content: Dict mapping slide_key to content dict with
            slide_title, chart_path, and summary

    Returns:
        Combined PowerPoint presentation
    """
    try:
        slide_presentations = []

        for slide_key, content in slide_content.items():
            slide_title = content['slide_title']
            chart_path = content.get('chart_path', '')
            summary = content.get('summary', '')

            chart = chart_path if chart_path and Path(chart_path).exists() else ""
            slide_prs = create_slide(
                slide_title=slide_title,
                chart_path=chart,
                summary_text=summary,
            )
            slide_presentations.append(slide_prs)

        return combine_presentations(slide_presentations)

    except Exception as e:
        logger.error(f"Presentation assembly failed: {str(e)}", exc_info=True)
        return create_error_presentation(str(e))
