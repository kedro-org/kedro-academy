"""Shared utilities for the graphrag project."""

from pathlib import Path
from typing import Any

from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings


def _get_openai_credentials() -> dict[str, Any]:
    """Load OpenAI credentials from Kedro config, cached after first call."""
    if not hasattr(_get_openai_credentials, "_credentials"):
        conf_path = Path(__file__).resolve().parents[2] / settings.CONF_SOURCE
        conf_loader = OmegaConfigLoader(conf_source=str(conf_path))
        credentials = conf_loader["credentials"]
        _get_openai_credentials._credentials = credentials["openai"]

    return _get_openai_credentials._credentials


def get_openai_api_key() -> str:
    """Return the OpenAI API key from Kedro credentials."""
    return _get_openai_credentials()["api_key"]


def get_openai_client():
    """Return an OpenAI client configured from Kedro credentials."""
    from openai import OpenAI

    credentials = _get_openai_credentials()
    client_kwargs = {"api_key": credentials["api_key"]}
    base_url = credentials.get("base_url")
    if base_url:
        client_kwargs["base_url"] = base_url

    return OpenAI(**client_kwargs)
