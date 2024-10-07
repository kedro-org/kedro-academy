"""
This is a boilerplate pipeline 'data_processing'
generated using Kedro 0.19.8
"""

import numpy as np
from keras.utils import to_categorical
from sklearn.model_selection import train_test_split


def convert_to_np(part, num_classes=2):
    images = []
    labels = []
    for file, func in part.items():
        image = func()
        images.append(image)
        labels.append(file[:1])
    images = np.array(images, dtype=np.int64)
    labels = np.array(labels, dtype=np.int64)
    labels = to_categorical(labels, num_classes=num_classes)
    return images, labels

def split_train_test_val(images, labels, test_split, val_split, random_state):
    X_train, X_test_val, y_train, y_test_val = train_test_split(images, labels, test_size=test_split+val_split, random_state=random_state, shuffle=True)
    X_val, X_test, y_val, y_test = train_test_split(X_test_val, y_test_val, test_size=test_split/val_split, random_state=random_state, shuffle=True)
    return X_train, X_val, X_test, y_train, y_val, y_test
