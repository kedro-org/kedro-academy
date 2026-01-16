"""Preprocessing pipelines for SA and MA slide generation."""

from kedro.pipeline import Pipeline, node

from .nodes import (
    parse_slide_instructions,
    extract_slide_objectives,
    prepare_sa_slides,
    prepare_ma_slides,
)


def create_sa_preprocessing_pipeline() -> Pipeline:
    """Create the SA preprocessing pipeline with 3 nodes.

    Returns unified format: {"slides": {...}}
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
        node(
            func=prepare_sa_slides,
            inputs="base_slides",
            outputs="slide_configs",
            name="prepare_sa_slides",
            tags=["preprocessing", "deterministic"],
        ),
    ])


def create_ma_preprocessing_pipeline() -> Pipeline:
    """Create the MA preprocessing pipeline with 3 nodes.

    Returns agent-specific views:
    {
        "planner_slides": {...},
        "chart_slides": {...},
        "summarizer_slides": {...}
    }
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
        node(
            func=prepare_ma_slides,
            inputs="base_slides",
            outputs="slide_configs",
            name="prepare_ma_slides",
            tags=["preprocessing", "deterministic"],
        ),
    ])


def create_pipeline(**kwargs) -> Pipeline:
    """Create the default preprocessing pipeline (SA version)."""
    return create_sa_preprocessing_pipeline()
