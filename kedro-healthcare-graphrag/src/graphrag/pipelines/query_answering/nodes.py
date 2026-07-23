"""Query answering pipeline — agentic node with tool calling."""
import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone

import networkx as nx

from kedro.pipeline.llm_context import LLMContext

logger = logging.getLogger(__name__)

# ── Tool definitions sent to OpenAI ──────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Graph-aware semantic search over the healthcare knowledge base. "
                "Embeds the query, retrieves the most relevant entity summaries from ChromaDB, "
                "then automatically enriches each result with its 1-hop knowledge graph neighbours. "
                "Always call this first — it provides both statistical summaries and graph relationships."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results to return (default 4).",
                        "default": 4,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_graph_context",
            "description": (
                "Retrieve 1-hop neighbours of a specific named entity from the knowledge graph. "
                "Use this for targeted follow-up lookups when you need deeper graph context "
                "for a particular entity not covered by the initial search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Exact name of the entity node in the graph.",
                    },
                },
                "required": ["entity_name"],
            },
        },
    },
]


# ── Core retrieval helpers ────────────────────────────────────────────────────

def _search_knowledge_base(chroma_collection, openai_client, graph, query: str, n_results: int = 4) -> str:
    embedding = openai_client.embeddings.create(
        input=[query], model="text-embedding-3-small"
    ).data[0].embedding
    results = chroma_collection.query(query_embeddings=[embedding], n_results=n_results)
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    parts = []
    for doc, meta in zip(docs, metas):
        entity = meta.get("entity_name", "unknown")
        graph_ctx = _get_graph_context(graph, entity) if entity != "unknown" else ""
        section = f"[{entity}]\n{doc}"
        if graph_ctx:
            section += f"\n\n{graph_ctx}"
        parts.append(section)

    return "\n\n---\n\n".join(parts)


def _get_graph_context(graph, entity_name: str) -> str:
    if graph is None:
        return "Knowledge graph not available."
    if entity_name not in graph:
        candidates = [n for n in graph.nodes if entity_name.lower() in n.lower()]
        if not candidates:
            return f"Entity '{entity_name}' not found in graph."
        entity_name = candidates[0]

    neighbors = list(graph.neighbors(entity_name))
    rel_groups: dict = {}
    for n in neighbors:
        rel = graph[entity_name][n].get("relationship", "CONNECTED_TO")
        weight = graph[entity_name][n].get("weight", 0)
        rel_groups.setdefault(rel, []).append(f"{n} ({weight:,} patients)")

    lines = [f"Graph neighbours of '{entity_name}':"]
    for rel, nodes in rel_groups.items():
        lines.append(f"  {rel}: {', '.join(nodes)}")
    return "\n".join(lines)


# ── Tool builders for LLMContextNode ─────────────────────────────────────────

def build_search_tool(knowledge_graph: nx.Graph, chroma_collection) -> Callable:
    """Build a graph-aware search callable bound to the given ChromaDB collection and graph.

    Accepts either a dict (as returned by ChromaDBDataset._load) or a live chromadb Collection.
    """
    import chromadb
    from openai import OpenAI
    from graphrag.utils import get_openai_api_key

    if isinstance(chroma_collection, dict):
        # ChromaDBDataset._load() returns a plain dict — rebuild in-memory from pre-computed embeddings.
        client_obj = chromadb.EphemeralClient()
        collection = client_obj.create_collection("healthcare_knowledge")
        collection.add(
            documents=chroma_collection["documents"],
            ids=chroma_collection["ids"],
            metadatas=chroma_collection["metadatas"],
            embeddings=chroma_collection["embeddings"],
        )
    else:
        collection = chroma_collection

    openai_client = OpenAI(api_key=get_openai_api_key())

    def search_knowledge_base(query: str, n_results: int = 4) -> str:
        return _search_knowledge_base(collection, openai_client, knowledge_graph, query, n_results)

    return search_knowledge_base


def build_graph_context_tool(knowledge_graph: nx.Graph) -> Callable:
    """Build a graph context callable bound to the given NetworkX graph."""
    def get_graph_context(entity_name: str) -> str:
        return _get_graph_context(knowledge_graph, entity_name)

    return get_graph_context


# ── Agent loop ────────────────────────────────────────────────────────────────

def _run_agent(
    question: str,
    prompt_template,
    openai_client,
    search_tool: Callable,
    graph_context_tool: Callable,
    model: str = "gpt-4o",
    max_iterations: int = 6,
) -> dict:
    messages = prompt_template.format_messages(question=question)
    messages = [{"role": m.type if m.type != "human" else "user", "content": m.content}
                for m in messages]

    tool_calls_log = []
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return {
                "answer": msg.content,
                "tool_calls": tool_calls_log,
                "iterations": iterations,
            }

        messages.append(msg)

        for tc in msg.tool_calls:
            fn = tc.function.name
            args = json.loads(tc.function.arguments)

            if fn == "search_knowledge_base":
                result = search_tool(query=args["query"], n_results=args.get("n_results", 4))
            elif fn == "get_graph_context":
                result = graph_context_tool(entity_name=args["entity_name"])
            else:
                result = f"Unknown tool: {fn}"

            tool_calls_log.append({"tool": fn, "args": args, "result": result})
            logger.info("  Tool call: %s(%s)", fn, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return {
        "answer": "Max iterations reached without a final answer.",
        "tool_calls": tool_calls_log,
        "iterations": iterations,
    }


# ── Kedro node ────────────────────────────────────────────────────────────────

def run_agent(context: LLMContext, sample_questions: list[str]) -> dict:
    """Run the OpenAI function-calling agent using an assembled LLMContext."""
    openai_client = context.llm
    agent_prompt = context.prompts["agent_prompt"]
    search_tool = context.tools["search_knowledge_base"]
    graph_context_tool = context.tools["get_graph_context"]

    logger.info("Running healthcare knowledge graph agent on %d questions…", len(sample_questions))

    results = []
    for i, question in enumerate(sample_questions, 1):
        logger.info("[%d/%d] %s", i, len(sample_questions), question)
        outcome = _run_agent(
            question=question,
            prompt_template=agent_prompt,
            openai_client=openai_client,
            search_tool=search_tool,
            graph_context_tool=graph_context_tool,
        )
        results.append({"question": question, **outcome})
        logger.info("  → answered in %d iteration(s)", outcome["iterations"])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-4o",
        "embedding_model": "text-embedding-3-small",
        "questions_answered": len(results),
        "results": results,
    }
    logger.info("Agent report complete — %d questions answered.", len(results))
    return report
