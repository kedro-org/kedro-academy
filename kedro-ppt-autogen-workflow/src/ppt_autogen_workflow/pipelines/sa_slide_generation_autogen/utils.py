"""Utility functions for single-agent AutoGen pipeline."""
from __future__ import annotations

from typing import Any

from ppt_autogen_workflow.base.utils import format_prompt


def format_sa_prompts(
    slides: dict[str, Any],
    user_prompt_template: Any,
) -> dict[str, str]:
    """Format prompts for all slides."""
    formatted_prompts = {}

    for slide_key, config in slides.items():
        slide_config_str = (
            f"Slide Title: {config['slide_title']}\n"
            f"Chart Instruction: {config['chart_instruction']}\n"
            f"Summary Instruction: {config['summary_instruction']}\n"
            f"Data Context: {config['data_context']}"
        )
        formatted_prompts[slide_key] = format_prompt(
            user_prompt_template,
            slide_config=slide_config_str,
        )

    return formatted_prompts
