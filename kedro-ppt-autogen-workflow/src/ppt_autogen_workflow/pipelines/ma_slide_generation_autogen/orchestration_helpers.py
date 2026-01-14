"""Helper functions for multi-agent orchestration.

This module contains helper functions used by the orchestrate_multi_agent_workflow node.
These are separated from nodes.py to keep node functions focused on pipeline logic.
"""
from __future__ import annotations

from typing import Any

from kedro.pipeline.llm_context import LLMContext

from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml


def create_agent_from_context(
    context: LLMContext,
    system_prompt_key: str,
    create_agent_func,
) -> Any:
    """Create an agent from LLMContext.

    Args:
        context: LLMContext containing llm, prompts, and tools
        system_prompt_key: Key for the system prompt in context.prompts
        create_agent_func: Function to create the agent

    Returns:
        Compiled agent instance
    """
    model_client = context.llm
    system_prompt = context.prompts.get(system_prompt_key)

    # Flatten tools - tool builder functions return lists of FunctionTools
    tools = []
    for tool_or_list in context.tools.values():
        if isinstance(tool_or_list, list):
            tools.extend(tool_or_list)
        else:
            tools.append(tool_or_list)

    system_prompt_text = (
        system_prompt.format() if hasattr(system_prompt, 'format')
        else str(system_prompt)
    )

    return create_agent_func(model_client, system_prompt_text, tools)


def parse_slide_requirements(
    slide_generation_requirements: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Parse slide requirements into agent-specific configurations.

    Args:
        slide_generation_requirements: Raw slide configuration from YAML

    Returns:
        Tuple of (planner_slides, chart_slides, summarizer_slides)
    """
    slide_definitions = parse_instructions_yaml(slide_generation_requirements)
    data_context = "Sales data available through agent tools"

    planner_slides = {}
    chart_slides = {}
    summarizer_slides = {}

    for slide_key, slide_config in slide_definitions.items():
        objective = slide_config.get('objective', {})
        slide_title = objective.get('slide_title', slide_key)
        chart_instruction = objective.get('chart_instruction', '')
        summary_instruction = objective.get('summary_instruction', '')

        planner_slides[slide_key] = {
            'slide_title': slide_title,
            'chart_instruction': chart_instruction,
            'summary_instruction': summary_instruction,
            'data_context': data_context,
        }

        chart_slides[slide_key] = {
            'slide_title': slide_title,
            'chart_instruction': chart_instruction,
            'data_context': data_context,
        }

        summarizer_slides[slide_key] = {
            'slide_title': slide_title,
            'summary_instruction': summary_instruction,
            'data_context': data_context,
        }

    return planner_slides, chart_slides, summarizer_slides


def format_prompt(template: Any, **kwargs) -> str:
    """Format a prompt template with given kwargs."""
    if hasattr(template, 'format'):
        return template.format(**kwargs)
    return str(template)


def format_all_prompts(
    planner_slides: dict[str, Any],
    chart_slides: dict[str, Any],
    summarizer_slides: dict[str, Any],
    planner_user_prompt: Any,
    chart_user_prompt: Any,
    summarizer_user_prompt: Any,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Format prompts for all agents and slides.

    Args:
        planner_slides: Planner slide configurations
        chart_slides: Chart slide configurations
        summarizer_slides: Summarizer slide configurations
        planner_user_prompt: Planner user prompt template
        chart_user_prompt: Chart user prompt template
        summarizer_user_prompt: Summarizer user prompt template

    Returns:
        Tuple of (planner_prompts, chart_prompts, summarizer_prompts)
    """
    # Format planner prompts
    planner_prompts = {}
    for slide_key, config in planner_slides.items():
        planner_prompts[slide_key] = format_prompt(
            planner_user_prompt,
            slide_title=config['slide_title'],
            chart_instruction=config['chart_instruction'],
            summary_instruction=config['summary_instruction'],
            data_context=config['data_context']
        )

    # Format chart prompts
    chart_prompts = {}
    for slide_key, config in chart_slides.items():
        chart_config_str = (
            f"Slide Title: {config['slide_title']}\n"
            f"Chart Instruction: {config['chart_instruction']}\n"
            f"Data Context: {config['data_context']}"
        )
        if hasattr(chart_user_prompt, 'format'):
            chart_prompts[slide_key] = chart_user_prompt.format(chart_config=chart_config_str)
        else:
            chart_prompts[slide_key] = str(chart_user_prompt).replace("{chart_config}", chart_config_str)

    # Format summarizer prompts (with placeholder for chart_status)
    summarizer_prompts = {}
    for slide_key, config in summarizer_slides.items():
        summarizer_config_str = (
            f"Summary Instruction: {config['summary_instruction']}\n"
            f"Data Context: {config['data_context']}"
        )
        if hasattr(summarizer_user_prompt, 'format'):
            summarizer_prompts[slide_key] = summarizer_user_prompt.format(
                summarizer_config=summarizer_config_str,
                chart_status="{chart_status}"
            )
        else:
            summarizer_prompts[slide_key] = str(summarizer_user_prompt).replace(
                "{summarizer_config}", summarizer_config_str
            )

    return planner_prompts, chart_prompts, summarizer_prompts
