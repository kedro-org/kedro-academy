from kedro.pipeline import Pipeline, node, pipeline

from .nodes import evaluate_model, split_data, train_model


def create_pipeline(**kwargs) -> Pipeline:
    pipe = pipeline(
        [
            node(
                func=split_data,
                inputs=["model_input_table", "params:model_options"],
                outputs=["X_train", "X_test", "y_train", "y_test"],
                name="split_data_node",
            ),
            node(
                func=train_model,
                inputs=["X_train", "y_train"],
                outputs="regressor",
                name="train_model_node",
            ),
            node(
                func=evaluate_model,
                inputs=["regressor", "X_test", "y_test"],
                outputs=None,
                name="evaluate_model_node",
            ),
        ]
    )
    ds_active_pipe = pipeline(
        pipe=pipe,
        inputs="model_input_table",
        namespace="active_modelling_pipeline",
    )
    ds_candidate_pipe = pipeline(
        pipe=pipe,
        inputs="model_input_table",
        namespace="candidate_modelling_pipeline",
    )

    return ds_active_pipe + ds_candidate_pipe
