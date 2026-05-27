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

    # `apply` writes back to live catalog entries (system_prompt, skill_text,
    # eval_cases) that are inputs to other pipelines, creating a cycle when
    # composed into __default__. It is a terminal, human-triggered step and
    # must always be run explicitly via `kedro run -p apply`.
    #
    # `scouts` is included in __default__ so a bare `kedro run` executes the
    # full observable loop: campaign → evaluation → scouts.
    pipelines["__default__"] = sum(
        v for k, v in pipelines.items() if k != "apply"
    )
    return pipelines
