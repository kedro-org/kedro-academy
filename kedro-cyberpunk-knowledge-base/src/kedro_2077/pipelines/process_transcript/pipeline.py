"""Pipeline for processing Cyberpunk 2077 transcript and wiki data."""

from kedro.pipeline import Node, Pipeline
from .nodes import (
    chunk_transcript,
    extract_characters,
    partition_transcript_chunks,
    embed_wiki_pages,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the process transcript pipeline."""
    return Pipeline(
        [
            Node(
                func=chunk_transcript,
                inputs="cyberpunk_transcript",
                outputs="raw_transcript_chunks",
                name="chunk_transcript",
            ),
            Node(
                func=partition_transcript_chunks,
                inputs="raw_transcript_chunks",
                outputs="transcript_chunks",
                name="partition_transcript_chunks",
            ),
            Node(
                func=extract_characters,
                inputs="cyberpunk_transcript",
                outputs="character_list",
                name="extract_characters",
            ),
            Node(
                func=embed_wiki_pages,
                inputs=["cyberpunk_wiki", "params:embedding_model_name"],
                outputs="wiki_embeddings",
                name="embed_wiki_pages_node",
            ),
        ]
    )
