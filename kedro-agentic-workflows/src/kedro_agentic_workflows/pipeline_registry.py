"""Project pipelines."""

from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines()
    pipelines["openai"] = pipelines["intent_detection"] + pipelines["response_generation_openai"]
    pipelines["__default__"] = pipelines["intent_detection"] + pipelines["response_generation"]
    # pipelines["__default__"] = sum(pipelines.values())
    return pipelines
