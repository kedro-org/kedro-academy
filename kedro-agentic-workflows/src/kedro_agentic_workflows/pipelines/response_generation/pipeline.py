from kedro.pipeline import Pipeline, node, pipeline, llm_context_node

from .nodes import (
    generate_response,
    log_response_and_end_session,
)
from .tools import build_lookup_docs, build_get_user_claims, build_create_claim


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="response_agent_context_node",
                outputs="response_generation_context",
                llm="llm",
                prompts=["tool_prompt", "response_prompt"],
                tools=[
                    {"func": build_get_user_claims, "inputs": ["db_engine"]},
                    {"func": build_lookup_docs, "inputs": ["docs", "params:docs_matches"]},
                    {"func": build_create_claim, "inputs": ["db_engine"]},
                ],
            ),
            node(
                func=generate_response,
                inputs=[
                    "response_generation_context",
                    "intent_detection_result",
                    "user_context",
                    "session_config",
                ],
                outputs="final_response",
                name="generate_response_node",
            ),
            node(
                func=log_response_and_end_session,
                inputs=["db_engine", "session_id", "final_response"],
                outputs=None,
                name="end_session_node",
            ),
        ]
    )
