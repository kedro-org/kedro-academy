"""Kedro nodes for single-agent AutoGen PPT generation pipeline.

This module uses LLMContext from llm_context_node to simplify agent creation.
"""
from __future__ import annotations

import logging
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from .agent import create_ppt_agent
from .agent_helpers import (
    generate_chart,
    generate_summary,
    create_slide_presentation,
    create_error_presentation,
)
# Import shared utilities from MA pipeline and utils
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen.presentation import (
    combine_presentations,
    format_summary_text,
)
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml

logger = logging.getLogger(__name__)


def generate_presentation(
    llm_context: LLMContext,
    slide_generation_requirements: dict[str, Any],
) -> Any:
    """Generate presentation using LLMContext.

    This function:
    1. Creates the PPT agent from LLMContext (llm + prompts + tools)
    2. Formats user prompts based on slide requirements
    3. Generates charts and summaries for each slide
    4. Combines slides into final presentation

    Args:
        llm_context: LLMContext containing llm, prompts, and tools
        slide_generation_requirements: Slide configuration from YAML

    Returns:
        PowerPoint presentation object
    """
    try:
        # Parse slide definitions from requirements
        slide_definitions = parse_instructions_yaml(slide_generation_requirements)
        ppt_requirement = {'slides': {}}
        data_context = "Sales data available through agent tools"

        for slide_key, slide_config in slide_definitions.items():
            objective = slide_config.get('objective', {})
            ppt_requirement['slides'][slide_key] = {
                'slide_title': objective.get('slide_title', slide_key),
                'chart_instruction': objective.get('chart_instruction', ''),
                'summary_instruction': objective.get('summary_instruction', ''),
                'data_context': data_context,
            }

        # Extract components from LLMContext
        model_client = llm_context.llm
        system_prompt = llm_context.prompts.get("ppt_generator_system_prompt")
        user_prompt_template = llm_context.prompts.get("ppt_generator_user_prompt")

        # Flatten tools - tool builder functions return lists of FunctionTools
        tools = []
        for tool_or_list in llm_context.tools.values():
            if isinstance(tool_or_list, list):
                tools.extend(tool_or_list)
            else:
                tools.append(tool_or_list)

        # Format system prompt
        system_prompt_text = system_prompt.format() if hasattr(system_prompt, 'format') else str(system_prompt)

        # Create the PPT agent
        agent = create_ppt_agent(model_client, system_prompt_text, tools)

        # Format user prompts for each slide
        formatted_prompts = {}
        for slide_key, slide_config in ppt_requirement['slides'].items():
            slide_config_str = (
                f"Slide Title: {slide_config['slide_title']}\n"
                f"Chart Instruction: {slide_config['chart_instruction']}\n"
                f"Summary Instruction: {slide_config['summary_instruction']}\n"
                f"Data Context: {slide_config['data_context']}"
            )
            if hasattr(user_prompt_template, 'format'):
                formatted_prompt = user_prompt_template.format(slide_config=slide_config_str)
            else:
                formatted_prompt = str(user_prompt_template).replace("{slide_config}", slide_config_str)
            formatted_prompts[slide_key] = formatted_prompt

        # Generate slides
        slide_configs = ppt_requirement['slides']
        slide_presentations = []

        for slide_key, config in slide_configs.items():
            slide_title = config['slide_title']
            user_prompt = formatted_prompts.get(slide_key, '')

            # Generate chart using formatted prompt
            chart_path = generate_chart(
                agent, user_prompt, slide_key, config.get('chart_instruction', '')
            )

            # Generate summary using formatted prompt (with chart status injected)
            summary_text = generate_summary(
                agent, user_prompt, slide_key, chart_path
            )
            formatted_summary = format_summary_text(summary_text)
            slide_prs = create_slide_presentation(slide_title, chart_path, formatted_summary)
            slide_presentations.append(slide_prs)

        return combine_presentations(slide_presentations)

    except Exception as e:
        logger.error(f"PPT generation failed: {str(e)}", exc_info=True)
        return create_error_presentation(str(e))
