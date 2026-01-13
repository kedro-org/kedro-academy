"""Kedro nodes for single-agent AutoGen PPT generation pipeline."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from autogen_ext.models.openai import OpenAIChatCompletionClient

from .agent import create_ppt_agent, PPTGenerationAgent
from .agent_helpers import (
    generate_chart,
    generate_summary,
    create_slide_presentation,
    create_error_presentation,
)
from .tools import build_tools
from ppt_autogen_workflow.utils.ppt_builder import combine_presentations
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml
from ppt_autogen_workflow.utils.node_helpers import format_summary_text

logger = logging.getLogger(__name__)


def init_tools(sales_data: pd.DataFrame) -> dict[str, Any]:
    """Initialize all tools needed for PPT generation agent."""
    return {"ppt_tools": build_tools(sales_data)}


def compile_ppt_agent(
    slide_generation_requirements: dict[str, Any],
    ppt_generator_system_prompt: Any,
    ppt_generator_user_prompt: Any,
    model_client: OpenAIChatCompletionClient,
    tools: dict[str, Any],
) -> PPTGenerationAgent:
    """Compile the PPT Generation Agent with requirements and formatted prompts."""
    try:
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

        system_prompt_text = ppt_generator_system_prompt.format()
        agent = create_ppt_agent(model_client, system_prompt_text, tools["ppt_tools"])
        agent._ppt_requirement = ppt_requirement

        # Format user prompts for each slide
        formatted_prompts = {}
        for slide_key, slide_config in ppt_requirement['slides'].items():
            slide_config_str = (
                f"Slide Title: {slide_config['slide_title']}\n"
                f"Chart Instruction: {slide_config['chart_instruction']}\n"
                f"Summary Instruction: {slide_config['summary_instruction']}\n"
                f"Data Context: {slide_config['data_context']}"
            )
            formatted_prompt = ppt_generator_user_prompt.format(slide_config=slide_config_str)
            formatted_prompts[slide_key] = formatted_prompt

        agent._formatted_prompts = formatted_prompts
        return agent

    except Exception as e:
        logger.error(f"Failed to compile PPT agent: {str(e)}", exc_info=True)
        raise


def generate_presentation(compiled_ppt_agent: PPTGenerationAgent) -> Any:
    """Generate presentation using compiled agent with formatted prompts."""
    try:
        slide_configs = compiled_ppt_agent._ppt_requirement['slides']
        formatted_prompts = compiled_ppt_agent._formatted_prompts
        slide_presentations = []

        for slide_key, config in slide_configs.items():
            slide_title = config['slide_title']
            user_prompt = formatted_prompts.get(slide_key, '')

            # Generate chart using formatted prompt
            chart_path = generate_chart(
                compiled_ppt_agent, user_prompt, slide_key, config.get('chart_instruction', '')
            )

            # Generate summary using formatted prompt (with chart status injected)
            summary_text = generate_summary(
                compiled_ppt_agent, user_prompt, slide_key, chart_path
            )
            formatted_summary = format_summary_text(summary_text)
            slide_prs = create_slide_presentation(slide_title, chart_path, formatted_summary)
            slide_presentations.append(slide_prs)

        return combine_presentations(slide_presentations)

    except Exception as e:
        logger.error(f"PPT generation failed: {str(e)}", exc_info=True)
        return create_error_presentation(str(e))
