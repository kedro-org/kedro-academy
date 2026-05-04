"""Project pipelines."""

from kedro.pipeline import Pipeline

from risk_profile_classifier.pipelines import serving, training


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    training_pipeline = training.create_pipeline()
    serving_pipeline = serving.create_pipeline()
    
    return {
        "training": training_pipeline,
        "serving": serving_pipeline,
        "__default__": training_pipeline,
    }
