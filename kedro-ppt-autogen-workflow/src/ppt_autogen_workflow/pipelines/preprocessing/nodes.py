"""Preprocessing functions for parsing instructions and preparing slide configurations.

This module contains deterministic functions that prepare data for
the agentic pipelines. No LLM calls or agent logic here.
These functions are reusable by both MA and SA pipelines.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_instructions_yaml(
    instructions_yaml: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Parse instructions_yaml to extract slide definitions.

    Extracts slide definitions from the 'iterative_slide_generation' section
    of the instructions YAML. Each slide definition must contain an 'objective'
    key with chart_instruction, summary_instruction, and slide_title.

    Args:
        instructions_yaml: Dictionary loaded from instructions.yaml file

    Returns:
        Dictionary mapping slide keys (e.g., 'slide_1') to slide definitions.
        Each definition contains 'objective' with:
        - chart_instruction: Natural language instruction for chart
        - summary_instruction: Natural language instruction for summary
        - slide_title: Title for the slide

    Example:
        >>> instructions = {
        ...     'iterative_slide_generation': {
        ...         'slide_1': {
        ...             'objective': {
        ...                 'chart_instruction': 'bar chart of top 10 products',
        ...                 'summary_instruction': 'summarize top performers',
        ...                 'slide_title': 'Top Products'
        ...             }
        ...         }
        ...     }
        ... }
        >>> slides = parse_instructions_yaml(instructions)
        >>> list(slides.keys())
        ['slide_1']
    """
    slide_definitions = {}

    if "iterative_slide_generation" in instructions_yaml:
        iterative_slides = instructions_yaml["iterative_slide_generation"]
        for slide_key, slide_data in iterative_slides.items():
            if isinstance(slide_data, dict) and "objective" in slide_data:
                slide_definitions[slide_key] = slide_data
            else:
                logger.warning(f"Skipping {slide_key} - missing 'objective' key")
    else:
        logger.warning("No 'iterative_slide_generation' found in instructions_yaml")

    return slide_definitions


def parse_slide_requirements(
    slide_generation_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Parse slide generation requirements from YAML into unified format.

    This deterministic function prepares slide configurations for both MA and SA pipelines.
    It extracts slide titles, chart instructions, and summary instructions into a unified
    format that works for any pipeline type.

    Args:
        slide_generation_requirements: Raw slide configuration from YAML

    Returns:
        Dictionary with 'slides' key containing slide configurations.
        Each slide has: slide_title, chart_instruction, summary_instruction, data_context
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
