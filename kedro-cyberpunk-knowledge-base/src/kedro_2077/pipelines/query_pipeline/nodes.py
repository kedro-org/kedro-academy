"""Query pipeline nodes for Cyberpunk 2077 transcript."""

from typing import Any, Dict, List
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from sentence_transformers import util
import torch

from kedro_2077.utils.utils import get_embedding_model, get_llm, get_openai_api_key


def find_relevant_contexts(
    query: str,
    transcript_chunks: Dict[str, Any],
    wiki_embeddings: Dict[str, Dict[str, Any]],
    character_list: List[str],
    embedding_model_name: str = "all-MiniLM-L6-v2",
    max_chunks: int = 5,
    character_bonus: float = 0.05,
    wiki_weight: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Retrieve top relevant contexts from both transcript chunks and wiki embeddings.

    Args:
        query: The user query string.
        transcript_chunks: PartitionedDataset with text chunks.
        wiki_embeddings: Dict with 'page_title' -> {'text': ..., 'embedding': np.ndarray}.
        character_list: Character names list to boost relevance.
        embedding_model_name: Name of the SentenceTransformer model to use.
        max_chunks: Max number of transcript chunks to return.
        character_bonus: Similarity boost for character matches.
        wiki_weight: Relative weight of wiki similarity when combining results.

    Returns:
        List of the most relevant text contexts (mixed transcript + wiki).
    """
    model = get_embedding_model(embedding_model_name)
    query_emb = model.encode(query, convert_to_tensor=True)

    # Characters mentioned in the query
    query_lower = query.lower()
    mentioned_characters = [c for c in character_list if c.lower() in query_lower]

    results = []

    # ---- Transcript similarity ----
    for chunk_data in transcript_chunks.values():
        if not isinstance(chunk_data, dict) or "text" not in chunk_data:
            continue
        text = chunk_data["text"]
        emb = model.encode(text, convert_to_tensor=True)
        sim = util.cos_sim(query_emb, emb).item()

        if mentioned_characters:
            for c in mentioned_characters:
                if c.lower() in text.lower():
                    sim += character_bonus

        results.append((sim, "transcript", text))

    # ---- Wiki similarity ----
    for title, page in wiki_embeddings.items():
        # Get embedding and convert to tensor if it isn't already
        emb = page["embedding"]
        if not isinstance(emb, torch.Tensor):
            emb = torch.tensor(emb)
        text = page["text"]

        sim = util.cos_sim(query_emb, emb).item() * wiki_weight
        results.append((sim, "wiki", f"{title}: {text[:1000]}..."))

    # Sort by score
    results.sort(key=lambda x: x[0], reverse=True)

    # Return top-N contexts
    top_results = [
        {"source": src, "text": txt, "similarity": sim}
        for sim, src, txt in results[:max_chunks]
    ]

    return top_results


def format_prompt_with_context(
    prompt_template: ChatPromptTemplate,
    user_query: str,
    contexts: List[Dict[str, Any]],
    max_context_length: int = 2000,
) -> List[BaseMessage]:
    """Format a ChatPromptTemplate with the user query and retrieved contexts.

    Combines the user's query with relevant context retrieved from the
    transcript and wiki, formatting them according to the prompt template.
    Contexts are truncated to the specified maximum length to fit within
    token limits.

    Args:
        prompt_template: LangChain ChatPromptTemplate to format.
        user_query: The user's question or query string.
        contexts: List of context dictionaries, each containing:
            - 'source': Either "transcript" or "wiki"
            - 'text': The context text
            - 'similarity': Similarity score (optional)
        max_context_length: Maximum length of each context block in characters.
            Defaults to 2000.

    Returns:
        List of formatted message objects ready to send to the LLM.
    """

    context_blocks = []
    for ctx in contexts:
        src_label = f"[{ctx['source'].upper()}]"
        truncated = ctx["text"][:max_context_length]
        context_blocks.append(f"{src_label}\n{truncated}")

    combined_context = "\n\n---\n\n".join(context_blocks)

    messages = prompt_template.format_messages(
        user_query=user_query, transcript_context=combined_context
    )

    return messages


def query_llm_cli(
    transcript_chunks: Dict[str, Any] = None,
    wiki_embeddings: Dict[str, Dict[str, Any]] = None,
    character_list: List[str] = None,
    embedding_model_name: str = "all-MiniLM-L6-v2",
    llm_model_name: str = "gpt-4o-mini",
    llm_temperature: float = 0.2,
    max_context_length: int = 2000,
    prompt_template: ChatPromptTemplate = None,
) -> None:
    """Interactive conversation loop for CLI chatbot interface.

    Provides an interactive command-line interface for querying the Cyberpunk
    2077 knowledge base. Maintains conversation history across multiple turns
    to enable follow-up questions and contextual responses.

    Args:
        transcript_chunks: PartitionedDataset containing transcript chunks.
        wiki_embeddings: Dictionary of wiki page embeddings.
        character_list: List of character names for relevance boosting.
        embedding_model_name: Name of the embedding model to use.
            Defaults to "all-MiniLM-L6-v2".
        llm_model_name: Name of the OpenAI model to use.
            Defaults to "gpt-4o-mini".
        llm_temperature: Sampling temperature for the LLM (0.0-2.0).
            Defaults to 0.2.
        max_context_length: Maximum length of context per chunk.
            Defaults to 2000.
        prompt_template: LangChain ChatPromptTemplate for formatting prompts.

    Returns:
        None. This function runs an interactive loop until the user exits.
    """
    # Initialize LLM with credentials and parameters
    api_key = get_openai_api_key()
    llm = get_llm(api_key=api_key, model=llm_model_name, temperature=llm_temperature)

    print("\nI am a machine that answers questions about Cyberpunk 2077!")
    print("Type your question about the game world or characters.")
    print("Type 'exit' to quit.\n")

    conversation_history: List[Any] = []

    while True:
        user_query = input("🟢 You: ").strip()
        if not user_query:
            continue
        if user_query.lower() in {"exit", "quit"}:
            print("👋 Goodbye, choom!")
            return ""

        # Re-find relevant contexts for each user query to ensure
        # the most up-to-date context is used based on the conversation flow
        contexts = find_relevant_contexts(
            query=user_query,
            transcript_chunks=transcript_chunks,
            wiki_embeddings=wiki_embeddings,
            character_list=character_list,
            embedding_model_name=embedding_model_name,
        )

        new_messages = format_prompt_with_context(
            prompt_template=prompt_template,
            user_query=user_query,
            contexts=contexts,
            max_context_length=max_context_length,
        )

        # Append new messages to conversation history
        conversation_history.extend(new_messages)
        response = llm.invoke(conversation_history)

        print("\n⚪ LLM:", response.content)
        print("\n" + "-" * 80 + "\n")

        # Append LLM response to conversation history for next turn
        conversation_history.append({"role": "ai", "content": response.content})


def query_llm_discord(
    formatted_prompt: List[BaseMessage],
    llm_model_name: str = "gpt-4o-mini",
    llm_temperature: float = 0.2,
) -> str:
    """Run a single LLM query for Discord bot usage.

    Processes a single query and returns the LLM response as a string.
    This function is designed for use in the Discord bot pipeline where
    each query is independent (no conversation history).

    Args:
        formatted_prompt: List of formatted message objects from
            format_prompt_with_context().
        llm_model_name: Name of the OpenAI model to use.
            Defaults to "gpt-4o-mini".
        llm_temperature: Sampling temperature for the LLM (0.0-2.0).
                        Defaults to 0.2.

    Returns:
        String containing the LLM's response to the query.

    Note:
        If the formatted_prompt is empty, returns a default error message.
    """
    if not formatted_prompt:
        return "Hey choom, I need a question to answer!"

    # Initialize LLM with credentials and parameters
    api_key = get_openai_api_key()
    llm = get_llm(api_key=api_key, model=llm_model_name, temperature=llm_temperature)

    # Run LLM
    response = llm.invoke(formatted_prompt)

    return response.content
