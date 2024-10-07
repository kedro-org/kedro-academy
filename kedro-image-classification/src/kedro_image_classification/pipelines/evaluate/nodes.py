"""
This is a boilerplate pipeline 'evaluate'
generated using Kedro 0.19.8
"""
import logging

import plotly.graph_objects as go


def evaluate_model(model, X_test, y_test):
    score = model.evaluate(X_test, y_test)
    logger = logging.getLogger(__name__)
    logger.info(f"Test Loss: {score[0]}")
    logger.info(f"Test Accuracy: {score[1]}")


def report(history):
    accuracy = history.history['accuracy']
    val_accuracy = history.history['val_accuracy']
    loss = history.history['loss']
    val_loss = history.history['val_loss']
    epochs = list(range(len(accuracy)))
    fig_accuracy = go.Figure()
    fig_accuracy.add_trace(go.Scatter(x=epochs, y=accuracy, mode='lines', name='Training accuracy', line=dict(color='blue')))

    # Add Validation accuracy trace
    fig_accuracy.add_trace(go.Scatter(x=epochs, y=val_accuracy, mode='lines', name='Validation accuracy', line=dict(color='red')))

    # Set title and labels
    fig_accuracy.update_layout(
        title='Training and Validation Accuracy',
        xaxis_title='Epochs',
        yaxis_title='Accuracy'
    )

    fig_loss = go.Figure()

    # Add Training loss trace
    fig_loss.add_trace(go.Scatter(x=epochs, y=loss, mode='lines', name='Training loss', line=dict(color='blue')))

    # Add Validation loss trace
    fig_loss.add_trace(go.Scatter(x=epochs, y=val_loss, mode='lines', name='Validation loss', line=dict(color='red')))

    # Set title and labels
    fig_loss.update_layout(
        title='Training and Validation Loss',
        xaxis_title='Epochs',
        yaxis_title='Loss'
    )



    return fig_accuracy, fig_loss
