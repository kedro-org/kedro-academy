"""Project pipelines."""
from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines(raise_errors=True)
    # Pipelines form a cycle across runs (apply→agent_run→eval→reflection→apply),
    # so there is no meaningful combined default. Use agent_run as the default
    # for `kedro run` without arguments.
    pipelines["__default__"] = pipelines.get("agent_run", Pipeline([]))
    return pipelines
