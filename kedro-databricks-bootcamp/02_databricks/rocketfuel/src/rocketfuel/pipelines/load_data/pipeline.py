"""
This is a boilerplate pipeline 'load_data'
generated using Kedro 0.19.10
"""

from kedro.pipeline import node, Pipeline, pipeline  # noqa
from .nodes import spark_from_pandas


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            # Your code goes here
            # node(
            #     func=...,
            #     inputs=...,
            #     outputs=...,
            #     name=...,
            # ),
            # node(
            #     func=...,
            #     inputs=...,
            #     outputs=...,
            #     name=...,
            # ),
            node(
                func=spark_from_pandas,
                inputs="shuttles_raw",
                outputs="shuttles",
                name="shuttles_load_node",
            ),
        ]
    )
