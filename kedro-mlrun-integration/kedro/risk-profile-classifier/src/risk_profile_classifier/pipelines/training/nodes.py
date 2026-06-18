"""Training pipeline nodes for risk profile classification."""
import logging
from typing import Dict, Tuple

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def load_and_prepare_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Load and prepare user data for risk profile classification.
    
    Args:
        raw_data: Raw user data from CSV file.
        
    Returns:
        DataFrame with user features and risk profile labels.
    """
    logger.info(f"Loaded {len(raw_data)} samples with distribution:")
    logger.info(raw_data["risk_profile"].value_counts().to_dict())
    
    # Drop user_id column if it exists (not needed for modeling)
    if "user_id" in raw_data.columns:
        raw_data = raw_data.drop(columns=["user_id"])
    
    return raw_data


def split_data(
    data: pd.DataFrame, parameters: Dict
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split data into training and test sets.
    
    Args:
        data: Input data with features and target.
        parameters: Parameters containing split configuration.
        
    Returns:
        X_train, X_test, y_train, y_test
    """
    feature_columns = parameters["features"]
    target_column = parameters["target"]
    test_size = parameters.get("test_size", 0.2)
    random_state = parameters.get("random_state", 42)
    
    X = data[feature_columns]
    y = data[target_column]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    logger.info(f"Training set size: {len(X_train)}")
    logger.info(f"Test set size: {len(X_test)}")
    
    return X_train, X_test, y_train, y_test


def preprocess_features(
    X_train: pd.DataFrame, X_test: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, StandardScaler]:
    """Scale features using StandardScaler.
    
    Args:
        X_train: Training features.
        X_test: Test features.
        
    Returns:
        Scaled X_train, X_test, and the fitted scaler.
    """
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train),
        columns=X_train.columns,
        index=X_train.index
    )
    X_test_scaled = pd.DataFrame(
        scaler.transform(X_test),
        columns=X_test.columns,
        index=X_test.index
    )
    
    logger.info("Features scaled using StandardScaler")
    
    return X_train_scaled, X_test_scaled, scaler


def train_classifier(
    X_train: pd.DataFrame, y_train: pd.Series, parameters: Dict
) -> RandomForestClassifier:
    """Train a Random Forest classifier for risk profile prediction.
    
    Args:
        X_train: Training features.
        y_train: Training labels.
        parameters: Model hyperparameters.
        
    Returns:
        Trained classifier model.
    """
    model_params = parameters.get("model_params", {})
    
    classifier = RandomForestClassifier(
        n_estimators=model_params.get("n_estimators", 100),
        max_depth=model_params.get("max_depth", 10),
        min_samples_split=model_params.get("min_samples_split", 5),
        random_state=model_params.get("random_state", 42),
        n_jobs=-1
    )
    
    classifier.fit(X_train, y_train)
    
    logger.info("Model trained successfully")
    logger.info(f"Feature importances: {dict(zip(X_train.columns, classifier.feature_importances_))}")
    
    return classifier


def evaluate_classifier(
    classifier: RandomForestClassifier,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict:
    """Evaluate the trained classifier.
    
    Args:
        classifier: Trained model.
        X_test: Test features.
        y_test: Test labels.
        
    Returns:
        Dictionary with evaluation metrics.
    """
    y_pred = classifier.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)
    class_report = classification_report(y_test, y_pred, output_dict=True)
    
    logger.info(f"Model Accuracy: {accuracy:.4f}")
    logger.info(f"Confusion Matrix:\n{conf_matrix}")
    logger.info(f"Classification Report:\n{classification_report(y_test, y_pred)}")
    
    metrics = {
        "accuracy": accuracy,
        "confusion_matrix": conf_matrix.tolist(),
        "classification_report": class_report
    }
    
    return metrics

