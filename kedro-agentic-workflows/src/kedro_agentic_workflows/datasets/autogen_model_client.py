from typing import Any, NoReturn, Optional

from kedro.io import AbstractDataset, DatasetError
from autogen_ext.models.openai import OpenAIChatCompletionClient


class OpenAIChatCompletionClientDataset(AbstractDataset[None, OpenAIChatCompletionClient]):
    """`OpenAIChatCompletionClientDataset` loads an autogen client for OpenAI
    chat completions.
    """
    def __init__(
        self,
        credentials: Optional[dict[str, str]] = None,
        kwargs: Optional[dict[str, Any]] = None
    ):
        self.credentials = credentials or {}
        self.kwargs = kwargs or {}

    def _describe(self) -> dict[str, Any]:
        credentials_masked = {k: "***" for k in self.credentials.keys()}
        return {**credentials_masked, **self.kwargs}

    def save(self, data: None) -> NoReturn:
        raise DatasetError(f"{self.__class__.__name__} is read-only and cannot save data")

    def load(self) -> OpenAIChatCompletionClient:
        return OpenAIChatCompletionClient(**self.credentials, **self.kwargs)
