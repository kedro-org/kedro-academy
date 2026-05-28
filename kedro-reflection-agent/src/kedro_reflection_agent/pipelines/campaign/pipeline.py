"""``campaign`` pipeline factory.

Generates one outreach email per (customer, product) input and emits one
Langfuse trace per generation. Evaluation is a separate concern.

Topology:
    llm_context_node  ->  agent_context (LLMContext)
    prepare_agent_inputs(targets, customers, products) -> agent_inputs
    generate_emails(agent_context, agent_inputs, skill_text,
                    agent_tracer, run_id, model_name, system_prompt_version)
        -> emails, run_metadata
"""

from kedro.pipeline import Pipeline, llm_context_node, node, pipeline

from .nodes import generate_emails, prepare_agent_inputs


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="agent_context_node",
                outputs="agent_context",
                llm="llm",
                prompts=["system_prompt"],
            ),
            node(
                func=prepare_agent_inputs,
                inputs=["targets", "customers", "products", "customer_profiles", "product_details"],
                outputs="agent_inputs",
                name="prepare_agent_inputs_node",
            ),
            node(
                func=generate_emails,
                inputs=[
                    "agent_context",
                    "agent_inputs",
                    "skill_text",
                    "agent_tracer",
                    "params:run_id",
                    "params:model_name",
                    "params:system_prompt_version",
                ],
                outputs=["emails", "run_metadata"],
                name="generate_emails_node",
            ),
        ]
    )
