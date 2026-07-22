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
    # graph_update writes to knowledge_graph (same output as graph_construction),
    # so it's excluded from __default__ to avoid a DAG conflict. Run it explicitly:
    #   kedro run --pipelines graph_update
    pipelines["__default__"] = sum(
        v for k, v in pipelines.items() if k != "graph_update"
    )
    return pipelines
