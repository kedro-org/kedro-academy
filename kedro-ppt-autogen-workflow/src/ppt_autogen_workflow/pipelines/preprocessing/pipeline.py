"""Preprocessing pipeline for parsing slide generation requirements.

This module defines preprocessing pipelines with 3 nodes each:
1. parse_slide_instructions - Parse raw YAML
2. extract_slide_objectives - Extract common objectives
3. prepare_sa_slides / prepare_ma_slides - Pipeline-specific preparation
"""

from kedro.pipeline import Pipeline, node

from .nodes import (
    parse_slide_instructions,
    extract_slide_objectives,
    prepare_sa_slides,
    prepare_ma_slides,
)


def create_sa_preprocessing_pipeline() -> Pipeline:
    """Create the SA preprocessing pipeline with 3 nodes."""
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
    """Create the MA preprocessing pipeline with 3 nodes."""
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
    """Create the default preprocessing pipeline (SA version).

    Returns:
        SA preprocessing pipeline with 3 nodes
    """
    return create_sa_preprocessing_pipeline()
