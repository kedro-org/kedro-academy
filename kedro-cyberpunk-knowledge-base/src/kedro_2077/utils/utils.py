"""Utility functions for the Kedro 2077 project."""

from pathlib import Path
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    """
    Lazy-load embedding model using a singleton pattern.

    The model is loaded only once and reused across all calls, which improves
    performance and reduces memory usage.

    Args:
        model_name: Name of the SentenceTransformer model to use.
                Defaults to "all-MiniLM-L6-v2".

    Returns:
        SentenceTransformer: The initialized embedding model instance.

    Example:
        >>> model = get_embedding_model("all-MiniLM-L6-v2")
        >>> embedding = model.encode("Hello world")
    """
    # Use function attribute to store the model (singleton pattern)
    if (
        not hasattr(get_embedding_model, "_model")
        or getattr(get_embedding_model, "_model_name", None) != model_name
    ):
        get_embedding_model._model = SentenceTransformer(model_name)
        get_embedding_model._model_name = model_name

    return get_embedding_model._model


def get_llm(
    api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.2
) -> ChatOpenAI:
    """
    Create a ChatOpenAI LLM instance with the specified configuration.

    This factory function creates LLM instances on demand, allowing for
    easy configuration and testing with different models and parameters.

    Args:
        api_key: OpenAI API key for authentication.
        model: Name of the OpenAI model to use. Defaults to "gpt-4o-mini".
        temperature: Sampling temperature (0.0 to 2.0). Higher values make
                    output more random. Defaults to 0.2.

    Returns:
        ChatOpenAI: The initialized LLM instance.

    Example:
        >>> llm = get_llm(api_key="sk-...", model="gpt-4o-mini", temperature=0.2)
        >>> response = llm.invoke("Hello!")
    """
    return ChatOpenAI(api_key=api_key, model=model, temperature=temperature)


def get_openai_api_key() -> str:
    """
    Lazy-load OpenAI API key from Kedro credentials.

    The credentials are loaded only when needed, and cached for subsequent calls.
    This avoids loading credentials at module import time.

    Returns:
        str: The OpenAI API key from credentials.

    Raises:
        KeyError: If the OpenAI API key is not found in credentials.

    Example:
        >>> api_key = get_openai_api_key()
        >>> llm = ChatOpenAI(api_key=api_key)
    """
    # Use function attribute to cache the API key (singleton pattern)
    if not hasattr(get_openai_api_key, "_api_key"):
        conf_path = Path(__file__).resolve().parents[3] / settings.CONF_SOURCE
        conf_loader = OmegaConfigLoader(conf_source=str(conf_path))
        credentials = conf_loader["credentials"]
        get_openai_api_key._api_key = credentials["openai"]["api_key"]

    return get_openai_api_key._api_key
