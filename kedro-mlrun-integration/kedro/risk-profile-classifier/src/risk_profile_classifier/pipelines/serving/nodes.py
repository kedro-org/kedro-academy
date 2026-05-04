"""Serving pipeline nodes for risk profile prediction."""
import logging
from typing import Dict

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def load_user_data_for_prediction(user_input: Dict, parameters: Dict) -> pd.DataFrame:
    """Load user data for prediction from input dictionary.

    This function accepts data from HTTP requests (via Nuclio) or falls back
    to sample users defined in ``parameters.yml`` under ``serving.sample_users``.

    Args:
        user_input: Dictionary or list of dictionaries with user features.
                   Can be a single user dict or a list of user dicts.
                   When empty or None the sample_users from parameters are used.
        parameters: Serving parameters; must contain a ``sample_users`` key with
                    a list of user feature dicts used as fallback input.

    Returns:
        DataFrame with user features to predict.
    """
    if not user_input or user_input == {}:
        sample_users = parameters["sample_users"]
        df = pd.DataFrame(sample_users)
        logger.info(f"Using sample data from parameters: {len(df)} users")
    else:
        # Convert single dict to list for uniform processing
        if isinstance(user_input, dict) and "age" in user_input:
            user_data = [user_input]
        elif isinstance(user_input, list):
            user_data = user_input
        else:
            # Assume it's wrapped in a 'data' key
            user_data = user_input.get("data", user_input)
            if isinstance(user_data, dict) and "age" in user_data:
                user_data = [user_data]

        df = pd.DataFrame(user_data)
        logger.info(f"Loaded {len(df)} users for prediction from input")

    return df


def preprocess_prediction_data(
    user_data: pd.DataFrame,
    scaler: StandardScaler,
    parameters: Dict
) -> pd.DataFrame:
    """Preprocess user data for prediction using the trained scaler.
    
    Args:
        user_data: Raw user feature data.
        scaler: Fitted StandardScaler from training.
        parameters: Parameters including feature list.
        
    Returns:
        Scaled feature data ready for prediction.
    """
    feature_columns = parameters["features"]
    
    # Ensure we have all required features
    X = user_data[feature_columns]
    
    # Scale features using the trained scaler
    X_scaled = pd.DataFrame(
        scaler.transform(X),
        columns=X.columns,
        index=X.index
    )
    
    logger.info(f"Preprocessed {len(X_scaled)} user records")
    
    return X_scaled


def predict_risk_profiles(
    classifier: RandomForestClassifier,
    user_data_scaled: pd.DataFrame,
) -> pd.DataFrame:
    """Predict risk profiles for users.
    
    Args:
        classifier: Trained risk profile classifier.
        user_data_scaled: Scaled user features.
        
    Returns:
        DataFrame with predictions and probabilities.
    """
    # Get predictions
    predictions = classifier.predict(user_data_scaled)
    
    # Get prediction probabilities
    probabilities = classifier.predict_proba(user_data_scaled)
    
    # Create results DataFrame
    results = pd.DataFrame({
        "predicted_risk_profile": predictions,
    })
    
    # Add probability columns for each class
    for idx, class_name in enumerate(classifier.classes_):
        results[f"probability_{class_name}"] = probabilities[:, idx]
    
    # Add confidence score (max probability)
    results["confidence"] = probabilities.max(axis=1)
    
    logger.info(f"Generated predictions for {len(results)} users")
    logger.info(f"Prediction distribution:\n{results['predicted_risk_profile'].value_counts()}")
    
    return results


def format_predictions_output(
    predictions: pd.DataFrame,
    original_data: pd.DataFrame
) -> pd.DataFrame:
    """Combine predictions with original user data for output.
    
    Args:
        predictions: Prediction results with probabilities.
        original_data: Original user feature data.
        
    Returns:
        Complete DataFrame with features and predictions.
    """
    output = pd.concat([original_data.reset_index(drop=True), predictions], axis=1)
    
    logger.info("Formatted prediction output")
    
    return output


def generate_prediction_summary(predictions_output: pd.DataFrame) -> Dict:
    """Generate a summary of predictions for reporting.
    
    Args:
        predictions_output: Complete prediction results.
        
    Returns:
        Dictionary with summary statistics.
    """
    summary = {
        "total_users": len(predictions_output),
        "risk_profile_distribution": predictions_output["predicted_risk_profile"].value_counts().to_dict(),
        "average_confidence": float(predictions_output["confidence"].mean()),
        "low_confidence_predictions": int((predictions_output["confidence"] < 0.6).sum()),
    }
    
    logger.info(f"Prediction Summary: {summary}")
    
    return summary

