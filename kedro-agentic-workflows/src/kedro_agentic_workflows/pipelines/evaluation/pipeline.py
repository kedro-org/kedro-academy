from kedro.pipeline import Pipeline, node, pipeline

from .nodes import test_ds_creation


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=test_ds_creation,
                inputs="eval_ds",
                outputs=None,
                name="test_ds_creation_node",
            ),
        ]
    )