from typing import Any, NoReturn, Optional
from kedro.io import AbstractDataset, DatasetError
from crewai.llm import LLM


class CrewAILLMDataset(AbstractDataset[None, LLM]):
    """Kedro dataset that returns a CrewAI LLM instance (LiteLLM / provider wrapper)."""

    def __init__(
        self,
        model: str,
        credentials: Optional[dict[str, str]] = None,
        kwargs: Optional[dict[str, Any]] = None,
    ):
        self.model = model
        self.credentials = credentials or {}
        self.kwargs = kwargs or {}

    def _describe(self) -> dict[str, Any]:
        masked = {k: "***" for k in (self.credentials.keys() if self.credentials else [])}
        return {"model": self.model, **masked, **self.kwargs}

    def save(self, data: None) -> NoReturn:
        raise DatasetError(f"{self.__class__.__name__} is read-only and cannot save data")

    def load(self) -> LLM:
        return LLM(model=self.model, **self.credentials, **self.kwargs)
