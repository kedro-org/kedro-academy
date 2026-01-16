"""Preprocessing functions for parsing instructions and preparing slide configurations.

This module contains deterministic functions that prepare data for
the agentic pipelines. No LLM calls or agent logic here.

The preprocessing pipeline has 3 nodes:
1. parse_slide_instructions - Parse raw YAML into slide definitions
2. extract_slide_objectives - Extract objectives shared by SA and MA
3. prepare_sa_slides / prepare_ma_slides - Pipeline-specific preparation
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_slide_instructions(
    slide_generation_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Parse raw YAML slide instructions into normalized definitions.

    This is the first node in the preprocessing pipeline.
    Extracts slide definitions from the 'iterative_slide_generation' section.

    Args:
        slide_generation_requirements: Dictionary loaded from instructions.yaml file

    Returns:
        Dictionary mapping slide keys to slide definitions with 'objective' key.
    """
    slide_definitions = {}

    if "iterative_slide_generation" in slide_generation_requirements:
        iterative_slides = slide_generation_requirements["iterative_slide_generation"]
        for slide_key, slide_data in iterative_slides.items():
            if isinstance(slide_data, dict) and "objective" in slide_data:
                slide_definitions[slide_key] = slide_data
            else:
                logger.warning(f"Skipping {slide_key} - missing 'objective' key")
    else:
        logger.warning("No 'iterative_slide_generation' found in requirements")

    return slide_definitions


def extract_slide_objectives(
    slide_definitions: dict[str, Any],
    data_context: str = "Sales data available through agent tools",
) -> dict[str, dict[str, Any]]:
    """Prepare deterministic slide objectives shared by SA and MA pipelines.

    This is the second node in the preprocessing pipeline.
    Extracts slide_title, chart_instruction, summary_instruction from objectives.

    Args:
        slide_definitions: Output from parse_slide_instructions
        data_context: Context string describing available data

    Returns:
        Dictionary mapping slide keys to objective dictionaries.
    """
    slides = {}

    for slide_key, slide_config in slide_definitions.items():
        objective = slide_config.get("objective", {})

        slides[slide_key] = {
            "slide_title": objective.get("slide_title", slide_key),
            "chart_instruction": objective.get("chart_instruction", ""),
            "summary_instruction": objective.get("summary_instruction", ""),
            "data_context": data_context,
        }

    return slides


def prepare_sa_slides(
    base_slides: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Prepare unified slide view for single-agent pipeline.

    This is the third node in the SA preprocessing pipeline.
    Wraps base slides in a unified format.

    Args:
        base_slides: Output from extract_slide_objectives

    Returns:
        Dictionary with 'slides' key containing all slide configurations.
    """
    return {"slides": base_slides}


def prepare_ma_slides(
    base_slides: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Prepare slide view for multi-agent pipeline.

    This is the third node in the MA preprocessing pipeline.
    Currently uses the same unified format as SA for compatibility.

    Args:
        base_slides: Output from extract_slide_objectives

    Returns:
        Dictionary with 'slides' key containing all slide configurations.
    """
    return {"slides": base_slides}
