"""Preprocessing functions for slide configuration preparation."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Agent-specific field projections for MA pipeline
AGENT_VIEWS = {
    "planner_slides": [
        "slide_title",
        "chart_instruction",
        "summary_instruction",
        "data_context",
    ],
    "chart_slides": [
        "slide_title",
        "chart_instruction",
        "data_context",
    ],
    "summarizer_slides": [
        "slide_title",
        "summary_instruction",
        "data_context",
    ],
}


def parse_slide_instructions(
    slide_generation_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Parse raw YAML slide instructions into normalized definitions."""
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
    """Extract slide objectives (title, chart/summary instructions) from definitions."""
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
    SA agent gets all fields for each slide in a unified format.

    Args:
        base_slides: Output from extract_slide_objectives

    Returns:
        Dictionary with 'slides' key containing all slide configurations.
    """
    return {"slides": base_slides}


def _project_agent_view(
    base_slides: dict[str, dict[str, Any]],
    fields: list[str],
) -> dict[str, dict[str, Any]]:
    """Project only specified fields for each slide."""
    return {
        slide_key: {field: slide[field] for field in fields if field in slide}
        for slide_key, slide in base_slides.items()
    }


def prepare_ma_slides(
    base_slides: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Prepare agent-specific slide views for multi-agent pipeline.

    This is the third node in the MA preprocessing pipeline.
    Each MA agent gets only the fields relevant to its task:
    - planner_slides: all fields (to plan the full slide)
    - chart_slides: slide_title, chart_instruction, data_context
    - summarizer_slides: slide_title, summary_instruction, data_context

    Args:
        base_slides: Output from extract_slide_objectives

    Returns:
        Dictionary with agent-specific slide views.
    """
    return {
        agent_name: _project_agent_view(base_slides, fields)
        for agent_name, fields in AGENT_VIEWS.items()
    }
