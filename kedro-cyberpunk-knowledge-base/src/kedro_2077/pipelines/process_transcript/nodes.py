"""Nodes for processing the Cyberpunk 2077 transcript and wiki data."""

import re
from typing import Any, Dict, List
from tqdm import tqdm

from kedro_2077.utils.utils import get_embedding_model


def chunk_transcript(
    transcript: str, chunk_size: int = 1000, overlap: int = 200
) -> List[Dict[str, Any]]:
    """Split the transcript into overlapping chunks for better context retrieval.

    The transcript is split into overlapping chunks to ensure that context
    spanning chunk boundaries is not lost. This improves the quality of
    semantic search when retrieving relevant context for queries.

    Args:
        transcript: The full transcript text to chunk.
        chunk_size: Number of sentences per chunk. Defaults to 1000.
        overlap: Number of sentences to overlap between chunks. Defaults to 200.

    Returns:
        List of dictionaries, each containing:
        - 'text': The chunk text content
        - 'chunk_id': Unique identifier for the chunk
        - 'start_sentence': Starting sentence index
        - 'end_sentence': Ending sentence index
        - 'character_count': Length of the chunk in characters
    """
    # Clean up whitespaces
    cleaned_transcript = re.sub(r"\n+", "\n", transcript.strip())

    # Split into sentences/paragraphs
    sentences = re.split(r"(?<=[.!?])\s+", cleaned_transcript)

    chunks = []
    start_idx = 0

    while start_idx < len(sentences):
        end_idx = min(start_idx + chunk_size, len(sentences))
        chunk_text = " ".join(sentences[start_idx:end_idx])

        chunks.append(
            {
                "text": chunk_text,
                "chunk_id": len(chunks),
                "start_sentence": start_idx,
                "end_sentence": end_idx - 1,
                "character_count": len(chunk_text),
            }
        )

        # Move start_idx forward by chunk_size - overlap
        start_idx = max(start_idx + chunk_size - overlap, start_idx + 1)

    return chunks


def extract_characters(transcript: str) -> List[str]:
    """Extract unique character names from the transcript.

    Character names are identified by lines that start with text followed
    by a colon (e.g., "Johnny Silverhand: Hello there").

    Args:
        transcript: The full transcript text to extract characters from.

    Returns:
        Sorted list of unique character names found in the transcript.
    """
    # Pattern to match character names (usually followed by a colon)
    character_pattern = r"^([A-Za-z\s]+):"

    characters = set()
    for line in transcript.split("\n"):
        match = re.match(character_pattern, line.strip())
        if match:
            character_name = match.group(1).strip()
            if character_name and len(character_name) > 1:
                characters.add(character_name)

    return sorted(list(characters))


def partition_transcript_chunks(
    chunks: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Convert a list of chunk dicts into a partition mapping for Kedro's PartitionedDataset.

    This function transforms a list of chunk dictionaries into the format
    required by Kedro's PartitionedDataset, where each chunk becomes a
    separate partition that can be stored and loaded independently.

    Args:
        chunks: List of chunk dictionaries from chunk_transcript().

    Returns:
        Dictionary mapping partition keys (e.g., "chunk_0", "chunk_1") to
        chunk data dictionaries. Example:
        {"chunk_0": {"text": "...", "chunk_id": 0, ...}, "chunk_1": {...}}
    """
    partitions: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        if chunk_id is None:
            # fallback to index position
            chunk_id = len(partitions)

        partition_key = f"chunk_{chunk_id}"
        partitions[partition_key] = chunk

    return partitions


def embed_wiki_pages(
    wiki_data: Dict[str, str], embedding_model_name: str = "all-MiniLM-L6-v2"
) -> Dict[str, Dict[str, Any]]:
    """Compute embeddings for each wiki page using SentenceTransformer.

    Generates semantic embeddings for wiki page content, enabling similarity
    search for retrieving relevant context during query processing.

    Args:
        wiki_data: Dictionary where keys are page titles and values are
            plain text content of the wiki pages.
        embedding_model_name: Name of the SentenceTransformer model to use.
            Defaults to "all-MiniLM-L6-v2".

    Returns:
        Dictionary mapping page titles to dictionaries containing:
        - 'text': Original page text content
        - 'embedding': NumPy array containing the semantic embedding vector
    """
    model = get_embedding_model(embedding_model_name)
    embedded_pages: Dict[str, Dict[str, Any]] = {}

    print(f"🧠 Embedding {len(wiki_data)} wiki pages...")
    for title, text in tqdm(wiki_data.items()):
        if not text.strip():
            continue
        embedding = model.encode(text, convert_to_numpy=True)
        embedded_pages[title] = {"text": text, "embedding": embedding}

    print(f"✅ Embedded {len(embedded_pages)} pages successfully.")
    return embedded_pages
