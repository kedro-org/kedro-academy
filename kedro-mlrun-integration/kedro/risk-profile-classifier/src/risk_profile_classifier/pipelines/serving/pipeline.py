"""Serving pipeline for risk profile prediction."""
from kedro.pipeline import Pipeline, node

from .nodes import (
    format_predictions_output,
    generate_prediction_summary,
    load_user_data_for_prediction,
    preprocess_prediction_data,
    predict_risk_profiles,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the serving/inference pipeline.
    
    Returns:
        A Pipeline object for serving predictions.
    """
    return Pipeline(
        [
            node(
                func=load_user_data_for_prediction,
                inputs="user_input",
                outputs="user_data_raw",
                name="load_user_data_node",
            ),
            node(
                func=preprocess_prediction_data,
                inputs=["user_data_raw", "feature_scaler", "params:serving"],
                outputs="user_data_scaled",
                name="preprocess_user_data_node",
            ),
            node(
                func=predict_risk_profiles,
                inputs=["risk_classifier", "user_data_scaled"],
                outputs="predictions",
                name="predict_risk_profiles_node",
            ),
        ]
    )

