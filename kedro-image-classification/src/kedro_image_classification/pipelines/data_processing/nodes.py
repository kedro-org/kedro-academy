"""
This is a boilerplate pipeline 'data_processing'
generated using Kedro 0.19.8
"""

import numpy as np
import random
from keras.utils import to_categorical
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt


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

def preview_train_data(X_train, y_train):
    n_rows = 3
    n_cols = 5
    plt.figure(figsize=(15, 10))
    for i in range(n_rows*n_cols):
        ax = plt.subplot(n_rows, n_cols, i + 1)
        ax.set_yticklabels([])
        ax.set_xticklabels([])
        index = random.randint(0, len(X_train) - 1)
        plt.imshow(X_train[index])
        plt.title(y_train[index])
    return plt
