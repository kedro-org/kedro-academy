"""Training pipeline for risk profile classifier."""
from kedro.pipeline import Pipeline, node

from .nodes import (
    evaluate_classifier,
    load_and_prepare_data,
    preprocess_features,
    split_data,
    train_classifier,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the training pipeline.
    
    Returns:
        A Pipeline object for training the risk profile classifier.
    """
    return Pipeline(
        [
            node(
                func=load_and_prepare_data,
                inputs="raw_user_data",
                outputs="prepared_user_data",
                name="load_data_node",
            ),
            node(
                func=split_data,
                inputs=["prepared_user_data", "params:training"],
                outputs=["X_train", "X_test", "y_train", "y_test"],
                name="split_data_node",
            ),
            node(
                func=preprocess_features,
                inputs=["X_train", "X_test"],
                outputs=["X_train_scaled", "X_test_scaled", "feature_scaler"],
                name="preprocess_features_node",
            ),
            node(
                func=train_classifier,
                inputs=["X_train_scaled", "y_train", "params:training"],
                outputs="risk_classifier",
                name="train_classifier_node",
            ),
            node(
                func=evaluate_classifier,
                inputs=["risk_classifier", "X_test_scaled", "y_test"],
                outputs="model_metrics",
                name="evaluate_classifier_node",
            ),
        ]
    )

