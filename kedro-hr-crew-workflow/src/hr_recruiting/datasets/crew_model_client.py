from typing import Any, NoReturn, Optional

from kedro.io import AbstractDataset, DatasetError
from crewai.llm import LLM


class CrewAILLMFactory:
    """A pickle-safe factory that creates the LLM instance on demand.

    This is needed because CrewAI's LLM uses httpx clients with thread locks
    that cannot be pickled. The factory stores only the configuration and
    creates the LLM when needed.
    """

    def __init__(
        self,
        model: str,
        credentials: dict[str, str],
        kwargs: dict[str, Any],
    ):
        self.model = model
        self.credentials = credentials
        self.kwargs = kwargs

    def create(self) -> LLM:
        """Create a new LLM instance."""
        return LLM(model=self.model, **self.credentials, **self.kwargs)

    def __call__(self) -> LLM:
        """Allow factory() syntax."""
        return self.create()


class CrewAILLMDataset(AbstractDataset[None, CrewAILLMFactory]):
    """`CrewAILLMDataset` loads a pickle-safe CrewAI LLM factory.

    Returns a factory object instead of the LLM directly because CrewAI's
    LLM class contains unpicklable httpx clients. Use factory.create() or
    factory() to get the actual LLM instance.
    """

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
        credentials_masked = {k: "***" for k in self.credentials.keys()}
        return {"model": self.model, **credentials_masked, **self.kwargs}

    def save(self, data: None) -> NoReturn:
        raise DatasetError(f"{self.__class__.__name__} is read-only and cannot save data")

    def load(self) -> CrewAILLMFactory:
        return CrewAILLMFactory(
            model=self.model,
            credentials=self.credentials,
            kwargs=self.kwargs,
        )
