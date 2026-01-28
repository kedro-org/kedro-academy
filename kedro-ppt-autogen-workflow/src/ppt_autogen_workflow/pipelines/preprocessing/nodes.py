"""Shared preprocessing functions for slide configuration preparation.

This module contains only the shared preprocessing logic used by both
SA and MA pipelines. Pipeline-specific preparation functions
(prepare_sa_slides, prepare_ma_slides) are in their respective pipeline modules.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


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
