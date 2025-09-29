from typing import Any, Literal

from kedro.io import AbstractDataset
from langfuse import Langfuse


class LangfuseTraceDataset(AbstractDataset):
    """
    Kedro dataset for managing Langfuse tracing clients and callbacks.
    Returns appropriate tracing objects based on mode configuration.

    Modes:
    - langchain: Returns CallbackHandler for LangChain integration
    - openai: Returns wrapped OpenAI client with automatic tracing
    - sdk: Returns raw Langfuse client for manual tracing
    """

    def __init__(
        self,
        credentials: dict[str, Any],
        mode: Literal["langchain", "openai", "sdk"] = "sdk",
        **trace_kwargs
    ):
        """
        Args:
            credentials: Dict with Langfuse credentials {public_key, secret_key, host}.
            mode: Tracing mode - "langchain", "openai", or "sdk".
            **trace_kwargs: Additional kwargs passed to the tracing client.
        """
        self._credentials = credentials
        self._mode = mode
        self._trace_kwargs = trace_kwargs

    def _describe(self):
        return {"mode": self._mode, "credentials": "***"}

    def load(self):
        """
        Load appropriate tracing client based on mode.
        
        Returns:
            - langchain mode: CallbackHandler for LangChain callbacks
            - openai mode: Wrapped OpenAI client with tracing
            - sdk mode: Raw Langfuse client
        """
        if self._mode == "langchain":
            from langfuse.langchain import CallbackHandler
            return CallbackHandler()
        elif self._mode == "openai":
            from langfuse.openai import OpenAI
            return OpenAI()
        else:
            return Langfuse(
                public_key=self._credentials["public_key"],
                secret_key=self._credentials["secret_key"],
                host=self._credentials["host"]
            )

    def save(self, data):
        """Tracing datasets are read-only."""
        raise NotImplementedError("LangfuseTraceDataset is read-only - it provides tracing clients, not data storage")
