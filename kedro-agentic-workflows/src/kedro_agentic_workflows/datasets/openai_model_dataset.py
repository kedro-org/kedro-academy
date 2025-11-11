import os
from typing import Any, NoReturn

from agents import ModelSettings
from pydantic import BaseModel
from kedro.io import AbstractDataset, DatasetError


class OpenAIModelConfig(BaseModel):
    """Container for model name and settings for OpenAI Agents SDK."""
    name: str
    settings: ModelSettings


class OpenAIModelDataset(AbstractDataset[None, OpenAIModelConfig]):
    """Kedro dataset that sets OpenAI credentials and returns model configuration."""

    def __init__(
        self,
        credentials: dict[str, str],
        model_name: str,
        model_settings: dict[str, Any] | None = None,
    ):
        """
        Args:
            credentials: Must include `openai_api_key` and optionally `openai_api_base`.
            model_name: Name of the OpenAI model, e.g., "gpt-4o-mini".
            model_settings: Optional settings (temperature, max_output_tokens, etc.)
        """
        if "openai_api_key" not in credentials:
            raise DatasetError("Missing `openai_api_key` in credentials.")

        self.api_key = credentials["openai_api_key"]
        self.api_base = credentials.get("openai_api_base", "https://api.openai.com/v1")

        self.model_name = model_name
        self.model_settings = model_settings or {}

    def _describe(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_settings": self.model_settings,
            "api_base": self.api_base,
        }

    def load(self) -> OpenAIModelConfig:
        # Set credentials as environment variables for OpenAI SDK
        os.environ["OPENAI_API_KEY"] = self.api_key
        os.environ["OPENAI_API_BASE"] = self.api_base

        return OpenAIModelConfig(
            name=self.model_name,
            settings=ModelSettings(**self.model_settings),
        )

    def save(self, data: None) -> NoReturn:
        raise DatasetError(f"{self.__class__.__name__} is read-only.")
