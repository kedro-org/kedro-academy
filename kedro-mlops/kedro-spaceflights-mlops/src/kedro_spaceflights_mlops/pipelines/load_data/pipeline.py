"""
This is a boilerplate pipeline 'load_data'
generated using Kedro 0.19.14
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import _noop


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
                func=_noop,
                inputs="shuttles_raw",
                outputs="shuttles",
                name="shuttles_load_node",
            ),
        ]
    )
