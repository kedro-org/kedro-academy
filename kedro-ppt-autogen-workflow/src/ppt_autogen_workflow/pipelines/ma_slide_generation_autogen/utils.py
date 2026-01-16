"""Utility functions for multi-agent AutoGen pipeline.

This module contains helper functions needed for the multi-agent
orchestration workflow.
"""
from __future__ import annotations

from typing import Any

from ppt_autogen_workflow.base.utils import format_prompt


def format_ma_prompts(
    planner_slides: dict[str, Any],
    chart_slides: dict[str, Any],
    summarizer_slides: dict[str, Any],
    planner_user_prompt: Any,
    chart_user_prompt: Any,
    summarizer_user_prompt: Any,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Format prompts for all agents using agent-specific slide views.

    Each agent receives only the fields relevant to its task:
    - Planner: all fields (slide_title, chart_instruction, summary_instruction, data_context)
    - Chart: slide_title, chart_instruction, data_context
    - Summarizer: slide_title, summary_instruction, data_context

    Args:
        planner_slides: Slide configs with all fields for planner
        chart_slides: Slide configs with chart-related fields only
        summarizer_slides: Slide configs with summary-related fields only
        planner_user_prompt: Planner user prompt template
        chart_user_prompt: Chart user prompt template
        summarizer_user_prompt: Summarizer user prompt template

    Returns:
        Tuple of (planner_prompts, chart_prompts, summarizer_prompts)
    """
    planner_prompts = {}
    chart_prompts = {}
    summarizer_prompts = {}

    # Format planner prompts (has all fields)
    for slide_key, config in planner_slides.items():
        planner_prompts[slide_key] = format_prompt(
            planner_user_prompt,
            slide_title=config['slide_title'],
            chart_instruction=config['chart_instruction'],
            summary_instruction=config['summary_instruction'],
            data_context=config['data_context']
        )

    # Format chart prompts (no summary_instruction)
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

    # Format summarizer prompts (no chart_instruction, with placeholder for chart_status)
    for slide_key, config in summarizer_slides.items():
        summarizer_config_str = (
            f"Slide Title: {config['slide_title']}\n"
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
