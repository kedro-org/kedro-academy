"""
This is a boilerplate pipeline 'data_processing'
generated using Kedro 0.19.8
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import convert_to_np, split_train_test_val


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=convert_to_np,
                inputs=["ships", "params:num_classes"],
                outputs=["images", "labels"],
                name="convert_to_np",
            ),
            node(
                func=split_train_test_val,
                inputs=["images", "labels", "params:test_size", "params:val_size", "params:random_state"],
                outputs=["ships_train", "ships_val", "ships_test", "labels_train", "labels_val", "labels_test"],
                name="split_train_test_val",
            ),

        ])
