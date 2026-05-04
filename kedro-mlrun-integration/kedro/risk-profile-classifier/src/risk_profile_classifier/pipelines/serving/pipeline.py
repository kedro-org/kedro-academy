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
        A Pipeline object for serving predictions. The final output is
        ``predictions`` — a DataFrame of user features combined with
        predicted risk profiles and confidence scores.
    """
    return Pipeline(
        [
            node(
                func=load_user_data_for_prediction,
                inputs=["user_input", "params:serving"],
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
                outputs="raw_predictions",
                name="predict_risk_profiles_node",
            ),
            node(
                func=format_predictions_output,
                inputs=["raw_predictions", "user_data_raw"],
                outputs="predictions",
                name="format_predictions_node",
            ),
            node(
                func=generate_prediction_summary,
                inputs="predictions",
                outputs="prediction_summary",
                name="generate_summary_node",
            ),
        ]
    )

