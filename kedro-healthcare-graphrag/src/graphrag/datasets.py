"""Custom Kedro datasets for the graphrag project."""

from kedro.io import AbstractDataset


class OpenAIClientDataset(AbstractDataset):
    """A read-only dataset that vends an OpenAI client loaded from Kedro credentials."""

    def __init__(self, metadata=None):
        pass

    def _load(self):
        from graphrag.utils import get_openai_client
        return get_openai_client()

    def _save(self, data):
        raise NotImplementedError("OpenAIClientDataset is read-only")

    def _describe(self):
        return {}
