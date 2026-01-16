"""Utility functions for multi-agent AutoGen pipeline.

This module contains helper functions needed for the multi-agent
orchestration workflow.
"""
from __future__ import annotations

from typing import Any

from ppt_autogen_workflow.base.utils import format_prompt


def format_ma_prompts(
    slides: dict[str, Any],
    planner_user_prompt: Any,
    chart_user_prompt: Any,
    summarizer_user_prompt: Any,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Format prompts for all agents using unified slides format.

    Args:
        slides: Unified slide configurations (same format as SA)
        planner_user_prompt: Planner user prompt template
        chart_user_prompt: Chart user prompt template
        summarizer_user_prompt: Summarizer user prompt template

    Returns:
        Tuple of (planner_prompts, chart_prompts, summarizer_prompts)
    """
    planner_prompts = {}
    chart_prompts = {}
    summarizer_prompts = {}

    for slide_key, config in slides.items():
        # Format planner prompt
        planner_prompts[slide_key] = format_prompt(
            planner_user_prompt,
            slide_title=config['slide_title'],
            chart_instruction=config['chart_instruction'],
            summary_instruction=config['summary_instruction'],
            data_context=config['data_context']
        )

        # Format chart prompt
        chart_config_str = (
            f"Slide Title: {config['slide_title']}\n"
            f"Chart Instruction: {config['chart_instruction']}\n"
            f"Data Context: {config['data_context']}"
        )
        if hasattr(chart_user_prompt, 'format'):
            chart_prompts[slide_key] = chart_user_prompt.format(chart_config=chart_config_str)
        else:
            chart_prompts[slide_key] = str(chart_user_prompt).replace("{chart_config}", chart_config_str)

        # Format summarizer prompt (with placeholder for chart_status)
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
