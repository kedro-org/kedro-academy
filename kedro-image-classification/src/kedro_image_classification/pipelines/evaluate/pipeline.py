"""
This is a boilerplate pipeline 'evaluate'
generated using Kedro 0.19.8
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import evaluate_model, report


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(
            func=evaluate_model,
            inputs=['fitted_model', 'ships_test', 'labels_test'],
            outputs=None
        ),
        node(
            func=report,
            inputs='history',
            outputs=["accuracy_plot", "loss_plot"],
        )
    ])
