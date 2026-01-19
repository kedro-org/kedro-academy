"""Shared preprocessing pipeline for slide generation.

This module contains only the shared preprocessing logic (2 nodes).
Pipeline-specific preparation is handled in the respective SA/MA pipeline modules.
"""

from kedro.pipeline import Pipeline, node

from .nodes import (
    parse_slide_instructions,
    extract_slide_objectives,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the shared preprocessing pipeline with 2 nodes.

    Outputs base_slides which is then transformed by pipeline-specific
    prepare_*_slides functions in the SA/MA pipelines.
    """
    return Pipeline([
        node(
            func=parse_slide_instructions,
            inputs="slide_generation_requirements",
            outputs="slide_definitions",
            name="parse_slide_instructions",
            tags=["preprocessing", "deterministic"],
        ),
        node(
            func=extract_slide_objectives,
            inputs="slide_definitions",
            outputs="base_slides",
            name="extract_slide_objectives",
            tags=["preprocessing", "deterministic"],
        ),
    ])
