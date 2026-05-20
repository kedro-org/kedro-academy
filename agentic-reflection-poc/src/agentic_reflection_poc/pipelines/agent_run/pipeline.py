from kedro.pipeline import Pipeline, llm_context_node, node, pipeline

from .nodes import generate_emails


def create_pipeline(**_kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="build_agent_llm_context",
                outputs="agent_llm_context",
                llm="agent_llm",
                prompts=["campaign_system_prompt"],
            ),
            node(
                generate_emails,
                inputs=[
                    "eval_cases_file",
                    "customers",
                    "products",
                    "skill_file",
                    "langfuse_tracer",
                    "agent_llm_context",
                    "parameters",
                ],
                outputs=["run_emails", "run_trace_metadata"],
                name="generate_emails",
            ),
        ]
    )
