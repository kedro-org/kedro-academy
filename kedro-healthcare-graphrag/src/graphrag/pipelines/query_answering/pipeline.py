"""Query answering pipeline."""
from kedro.pipeline import Pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from .nodes import build_graph_context_tool, build_search_tool, run_agent


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        llm_context_node(
            name="build_agent_context_node",
            outputs="agent_context",
            llm="openai_llm",
            prompts=["agent_prompt"],
            tools=[
                tool(build_search_tool, "knowledge_graph", "chroma_collection"),
                tool(build_graph_context_tool, "knowledge_graph"),
            ],
        ),
        node(
            func=run_agent,
            inputs=["agent_context", "params:sample_questions"],
            outputs="agent_report",
            name="run_agent_node",
        ),
    ])
