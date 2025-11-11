"""Query pipeline for Cyberpunk 2077 transcript."""

from kedro.pipeline import Node, Pipeline
from .nodes import find_relevant_contexts, format_prompt_with_context, query_llm_cli, query_llm_discord


def create_pipeline() -> Pipeline:
    """Create the query pipeline."""
    return Pipeline(
        [
            Node(
                func=find_relevant_contexts,
                inputs=["params:user_query", "transcript_chunks", "wiki_embeddings", "character_list", "params:embedding_model_name", "params:max_chunks", "params:character_bonus", "params:wiki_weight"],
                outputs="relevant_contexts",
                name="find_relevant_contexts",
                tags=["cli", "discord"],
            ),
            Node(
                func=format_prompt_with_context,
                inputs=["query_prompt", "params:user_query", "relevant_contexts", "params:max_context_length"],
                outputs="formatted_prompt",
                name="format_prompt_with_context",
                tags=["cli", "discord"],
            ),
            Node(
                func=query_llm_cli,
                inputs=["transcript_chunks", "wiki_embeddings", "character_list", "params:embedding_model_name", "params:llm_model_name", "params:llm_temperature", "params:max_context_length", "query_prompt"],
                outputs="llm_response_cli",
                name="query_llm_cli",
                tags=["cli"],
            ),
            Node(
                func=query_llm_discord,
                inputs=["formatted_prompt", "params:llm_model_name", "params:llm_temperature"],
                outputs="llm_response_discord",
                name="query_llm_discord",
                tags=["discord"],
            ),
        ]
    )