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
    pipeline_type: str = "ma",
) -> dict[str, Any]:
    """Parse slide generation requirements from YAML into structured format.

    This deterministic function prepares slide configurations for MA or SA pipelines.
    It extracts slide titles, chart instructions, and summary instructions.

    Args:
        slide_generation_requirements: Raw slide configuration from YAML
        pipeline_type: Type of pipeline - "ma" for multi-agent or "sa" for single-agent

    Returns:
        For MA pipeline:
            Dictionary with:
            - planner_slides: For planner agent
            - chart_slides: For chart generator agent
            - summarizer_slides: For summarizer agent
        For SA pipeline:
            Dictionary with:
            - slides: Unified slide configurations for single agent
    """
    slide_definitions = parse_instructions_yaml(slide_generation_requirements)
    data_context = "Sales data available through agent tools"

    if pipeline_type.lower() == "ma":
        # MA pipeline needs separate views for each agent
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

        return {
            'planner_slides': planner_slides,
            'chart_slides': chart_slides,
            'summarizer_slides': summarizer_slides,
        }
    else:
        # SA pipeline needs unified view
        sa_slides = {}

        for slide_key, slide_config in slide_definitions.items():
            objective = slide_config.get('objective', {})
            slide_title = objective.get('slide_title', slide_key)
            chart_instruction = objective.get('chart_instruction', '')
            summary_instruction = objective.get('summary_instruction', '')

            sa_slides[slide_key] = {
                'slide_title': slide_title,
                'chart_instruction': chart_instruction,
                'summary_instruction': summary_instruction,
                'data_context': data_context,
            }

        return {'slides': sa_slides}


def parse_ma_slide_requirements(
    slide_generation_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Parse slide generation requirements for MA pipeline.

    Wrapper function for parse_slide_requirements with pipeline_type="ma".

    Args:
        slide_generation_requirements: Raw slide configuration from YAML

    Returns:
        Dictionary with MA slide configurations:
        - planner_slides: For planner agent
        - chart_slides: For chart generator agent
        - summarizer_slides: For summarizer agent
    """
    return parse_slide_requirements(slide_generation_requirements, pipeline_type="ma")


def parse_sa_slide_requirements(
    slide_generation_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Parse slide generation requirements for SA pipeline.

    Wrapper function for parse_slide_requirements with pipeline_type="sa".

    Args:
        slide_generation_requirements: Raw slide configuration from YAML

    Returns:
        Dictionary with SA slide configurations:
        - slides: Unified slide configurations for single agent
    """
    return parse_slide_requirements(slide_generation_requirements, pipeline_type="sa")
