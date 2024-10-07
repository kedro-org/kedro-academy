"""
This is a boilerplate pipeline 'training'
generated using Kedro 0.19.8
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import compile_model, define_model, train_model


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(
            func=define_model,
            inputs=["params:input_shape", "params:num_classes"],
            outputs='model'
        ),
        node(
            func=compile_model,
            inputs=['model'],
            outputs='compiled_model'
        ),
        node(
            func=train_model,
            inputs=['compiled_model', 'ships_train', 'labels_train', 'ships_val', 'labels_val', 'params:epochs', 'params:batch_size'],
            outputs=['fitted_model', 'history']
        )
    ])
