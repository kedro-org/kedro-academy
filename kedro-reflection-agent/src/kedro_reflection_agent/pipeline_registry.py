"""Project pipelines."""
from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline


def register_pipelines() -> dict[str, Pipeline]:
    pipelines = find_pipelines()

    # Default = full agent loop: campaign → evaluation → scouts.
    # Apply and reflection are human-triggered; excluded from default.
    pipelines["__default__"] = (
        pipelines["campaign"]
        + pipelines["evaluation"]
        + pipelines["scouts"]
    )

    return pipelines
