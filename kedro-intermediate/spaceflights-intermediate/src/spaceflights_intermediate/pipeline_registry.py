"""Project pipelines."""
from typing import Dict

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline

#from .pipelines.data_processing import pipeline as dp
#from .pipelines.data_science import pipeline as ds


def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    pipelines = find_pipelines()
    pipelines["__default__"] = sum(pipelines.values())
    return pipelines
    # return {
    #     "__default__": dp.create_pipeline() + ds.create_pipeline(),
    #     "data_processing": dp.create_pipeline(),
    #     "data_science": ds.create_pipeline(),
    # }
