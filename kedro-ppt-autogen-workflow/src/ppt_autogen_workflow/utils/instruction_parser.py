"""Instruction parsing utilities for PPT generation pipelines.

This module provides shared utilities for parsing instruction YAML files
used by both single-agent and multi-agent pipelines.
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
        - csv_path_input: Path to the data file
        - chart_instruction: Natural language instruction for chart
        - summary_instruction: Natural language instruction for summary
        - slide_title: Title for the slide

    Example:
        >>> instructions = {
        ...     'iterative_slide_generation': {
        ...         'slide_1': {
        ...             'objective': {
        ...                 'csv_path_input': 'sales.csv',
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


def extract_slide_objective(
    slide_data: dict[str, Any],
) -> tuple[str, str, str, str]:
    """Extract objective fields from a slide definition.

    Args:
        slide_data: Dictionary containing slide definition with 'objective' key

    Returns:
        Tuple of (csv_path, chart_instruction, summary_instruction, slide_title)

    Raises:
        KeyError: If required fields are missing from objective
    """
    objective = slide_data["objective"]
    return (
        objective.get("csv_path_input", ""),
        objective.get("chart_instruction", ""),
        objective.get("summary_instruction", ""),
        objective.get("slide_title", "Untitled Slide"),
    )
