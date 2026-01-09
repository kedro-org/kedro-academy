from typing import Any, NoReturn

from deeplake.core.vectorstore import VectorStore
from kedro.io import AbstractDataset, DatasetError


class DeeplakeVectorStoreDataset(AbstractDataset[None, VectorStore]):
    """A Kedro dataset for interacting with DeepLake VectorStore.

    This dataset provides a read-only interface for loading a VectorStore instance
    from a specified Deep Lake path. It is useful for integrating vector search
    capabilities into a Kedro pipeline, such as for Retrieval-Augmented Generation (RAG) applications.

    More details: https://docs.activeloop.ai/examples/rag/tutorials/vector-store-basics
    """

    def __init__(self, path: str, **kwargs):
        """Initializes the dataset with the given Deep Lake path and optional parameters.

        Args:
            path: Path to the DeepLake VectorStore.
            **kwargs: Additional arguments for the VectorStore initialization.
        """
        self._path = path
        self.kwargs = kwargs or {}

    def load(self) -> VectorStore:
        """Loads and returns the DeepLake VectorStore from the specified path.

        Returns:
            VectorStore: An instance of the Deep Lake Vector Store.
        """
        return VectorStore(path=self._path, **self.kwargs)

    def save(self, data: None) -> NoReturn:
        """Raises an error because this dataset type is read-only.

        Args:
            data: This argument is unused as saving is not supported.

        Raises:
            DatasetError: Always raised since saving is not allowed.
        """
        raise DatasetError(f"{self.__class__.__name__} is a read only dataset type")

    def _describe(self) -> dict[str, Any]:
        """Returns a dictionary describing the dataset configuration.

        Returns:
            A dictionary containing the dataset path and additional parameters.
        """
        return {"filepath": self._path, **self.kwargs}
