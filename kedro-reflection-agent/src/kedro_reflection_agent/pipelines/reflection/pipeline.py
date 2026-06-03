"""``reflection`` pipeline factory.

The meta-agent reads the current prompt + skill file + evaluation scores and
produces four artifacts: a narrative summary, a proposed system prompt, a
proposed skill file, and new regression eval cases.

Topology:
    meta_agent_context_node
        -> meta_agent_context  (LLMContext)
    prepare_reflection_context(system_prompt, skill_text, per_case_scores,
                               aggregate_scores, eval_cases, passing_threshold)
        -> reflection_context
    reflect(meta_agent_context, reflection_context, run_id, reflection_id)
        -> reflection_summary, proposed_prompt, proposed_skill,
           proposed_eval_cases
"""

from kedro.pipeline import Pipeline, llm_context_node, node, pipeline

from .nodes import prepare_reflection_context, reflect


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="meta_agent_context_node",
                outputs="meta_agent_context",
                llm="meta_agent_llm",
                prompts=["meta_agent_prompt"],
            ),
            node(
                func=prepare_reflection_context,
                inputs=[
                    "system_prompt",
                    "skill_text",
                    "per_case_scores",
                    "aggregate_scores",
                    "eval_cases",
                    "params:passing_threshold",
                    "params:run_id",
                    "params:agent_id",
                ],
                outputs="reflection_context",
                name="prepare_reflection_context_node",
            ),
            node(
                func=reflect,
                inputs=[
                    "meta_agent_context",
                    "reflection_context",
                    "system_prompt",
                    "params:run_id",
                    "params:reflection_id",
                    "params:agent_id",
                ],
                outputs=[
                    "reflection_summary",
                    "proposed_prompt",
                    "proposed_skill",
                    "proposed_eval_cases",
                ],
                name="reflect_node",
            ),
        ]
    )
