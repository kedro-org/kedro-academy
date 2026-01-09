from typing import Any, Dict

import numpy as np
from kedro.io import AbstractDataset


class NumpyDataset(AbstractDataset):
    """A dataset class for loading numpy arrays."""

    def __init__(self, filepath: str):
        self._filepath = filepath
        self._data = None

    def _load(self) -> np.ndarray:
        """Load numpy array from the filepath."""
        return np.load(self._filepath)

    def _save(self, data: np.ndarray) -> None:
        """Save numpy array to the filepath."""
        self._data = data
        np.save(self._filepath, data)

    def _describe(self) -> Dict[str, Any]:
        """Describe the dataset."""
        return {"filepath": self._filepath, "shape": self._data.shape if self._data is not None else None}
