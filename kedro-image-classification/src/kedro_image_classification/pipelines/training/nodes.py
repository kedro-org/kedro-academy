"""
This is a boilerplate pipeline 'training'
generated using Kedro 0.19.8
"""
from keras.layers import (
    BatchNormalization,
    Conv2D,
    Dense,
    Dropout,
    Flatten,
    Input,
    LeakyReLU,
    MaxPooling2D,
)
from keras.models import Sequential


def define_model(input_shape = (80, 80, 3), n_classes = 2):
    model = Sequential()

    model.add(Input(shape=input_shape))

    model.add(Conv2D(32, (3, 3), activation='linear', padding='same'))
    model.add(LeakyReLU(negative_slope=0.1))
    model.add(MaxPooling2D((2, 2), padding='same'))
    model.add(Dropout(0.25))
    model.add(BatchNormalization())

    model.add(Conv2D(64, (3, 3), activation='linear', padding='same'))
    model.add(LeakyReLU(negative_slope=0.1))
    model.add(MaxPooling2D((2, 2), padding='same'))
    model.add(Dropout(0.25))
    model.add(BatchNormalization())

    model.add(Conv2D(128, (3, 3), activation='linear', padding='same'))
    model.add(LeakyReLU(negative_slope=0.1))
    model.add(MaxPooling2D((2, 2), padding='same'))
    model.add(Dropout(0.25))
    model.add(BatchNormalization())

    model.add(Conv2D(256, (3, 3), activation='linear', padding='same'))
    model.add(LeakyReLU(negative_slope=0.1))
    model.add(MaxPooling2D((2, 2), padding='same'))
    model.add(Dropout(0.25))
    model.add(BatchNormalization())

    model.add(Flatten())

    model.add(Dense(256, activation='linear'))
    model.add(LeakyReLU(negative_slope=0.1))
    model.add(Dropout(0.25))
    model.add(BatchNormalization())

    model.add(Dense(64, activation='linear'))
    model.add(LeakyReLU(negative_slope=0.1))
    model.add(Dropout(0.25))
    model.add(BatchNormalization())

    model.add(Dense(n_classes, activation='softmax'))

    return model

def compile_model(model, optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy']):
    model.compile(optimizer=optimizer, loss=loss, metrics=metrics)
    return model

def train_model(model, X_train, y_train, X_val, y_val, epochs, batch_size):
    history = model.fit(X_train, y_train, batch_size=batch_size, epochs=epochs, validation_data=(X_val, y_val), verbose=1)
    return model, history
