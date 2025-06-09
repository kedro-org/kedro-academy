"""
This is a boilerplate pipeline 'load_data'
generated using Kedro 0.19.10
"""

import pandas as pd

from kedro.pipeline import node, Pipeline, pipeline  # noqa
from .nodes import _noop, spark_from_pandas


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=_noop,
                inputs="companies_raw",
                outputs="companies",
                name="companies_load_node",
            ),
            node(
                func=_noop,
                inputs="reviews_raw",
                outputs="reviews",
                name="reviews_load_node",
            ),
            node(
                func=spark_from_pandas,
                inputs="shuttles_raw",
                outputs="shuttles",
                name="shuttles_load_node",
            ),
        ]
    )
