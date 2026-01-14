"""Project pipelines."""

from kedro.pipeline import Pipeline

from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen import (
    create_pipeline as create_ma_pipeline,
)


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    ma_pipeline = create_ma_pipeline()

    return {
        "__default__": ma_pipeline,
        "ma_slide_generation_autogen": ma_pipeline,
    }
