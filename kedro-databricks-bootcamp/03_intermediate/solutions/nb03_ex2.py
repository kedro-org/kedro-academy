import pytest
from rocketfuel.pipelines.data_science.nodes import split_data, train_model
from sklearn.linear_model import LinearRegression

def test_split_data(dummy_data, dummy_parameters):
    # Act
    X_train, X_test, y_train, y_test = split_data(dummy_data, dummy_parameters["model_options"])

    # Assert
    assert len(X_train) == 2
    assert len(y_train) == 2
    assert len(X_test) == 1
    assert len(y_test) == 1

def test_split_data_missing_price(dummy_data, dummy_parameters):
    dummy_data.pop("price")
    with pytest.raises(KeyError) as e_info:
        # Act
        X_train, X_test, y_train, y_test = split_data(dummy_data, dummy_parameters["model_options"])

    # Assert
    assert "price" in str(e_info.value) # checks that the error is about the missing price data

def test_train_model_returns_trained_model(dummy_X_train, dummy_y_train):
    # Act
    model = train_model(dummy_X_train, dummy_y_train)
    predictions = model.predict(dummy_X_train)
    
    # Assert
    assert isinstance(model, LinearRegression)
    assert hasattr(model, "coef_")
    assert hasattr(model, "intercept_")
    # Prediction check
    assert len(predictions) == len(dummy_y_train)
    for pred, actual in zip(predictions, dummy_y_train):
        assert abs(pred - actual) < 0.1  # Tolerance
