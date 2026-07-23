"""Shared utilities for the graphrag project."""

from pathlib import Path

from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings


def get_openai_api_key() -> str:
    """Load the OpenAI API key from Kedro credentials, cached after first call."""
    if not hasattr(get_openai_api_key, "_api_key"):
        conf_path = Path(__file__).resolve().parents[2] / settings.CONF_SOURCE
        conf_loader = OmegaConfigLoader(conf_source=str(conf_path))
        credentials = conf_loader["credentials"]
        get_openai_api_key._api_key = credentials["openai"]["api_key"]

    return get_openai_api_key._api_key
