from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    create_agent,
    create_agent_executor,
    create_chat_prompt,
    create_tools,
    init_llm,
    user_interaction_loop,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=create_tools,
                inputs=["vector_store_load", "embedding_function"],
                outputs="tools",
                name="create_tools_node",
            ),
            node(
                func=init_llm,
                inputs=["openai_llm", "tools"],
                outputs=["llm", "llm_with_tools"],
                name="init_llm_node",
            ),
            node(
                func=create_chat_prompt,
                inputs=["system_prompt"],
                outputs="chat_prompt",
                name="create_chat_prompt_node",
            ),
            node(
                func=create_agent,
                inputs=["llm_with_tools", "chat_prompt"],
                outputs="agent",
                name="create_agent_node",
            ),
            node(
                func=create_agent_executor,
                inputs=["agent", "tools"],
                outputs="agent_executor",
                name="create_agent_executor_node",
            ),
            node(
                func=user_interaction_loop,
                inputs=["agent_executor", "llm"],
                outputs="user_interaction_output",
                name="user_interaction_loop_node",
            ),
        ],
        tags="agent_rag"
    )
