from kedro.pipeline import Pipeline, llm_context_node, node, pipeline

from .nodes import build_reflection_proposal, split_proposal_outputs


def create_pipeline(**_kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="build_reflection_llm_context",
                outputs="reflection_llm_context",
                llm="reflection_llm",
                prompts=["campaign_system_prompt"],
            ),
            node(
                build_reflection_proposal,
                inputs=[
                    "run_emails",
                    "run_case_scores",
                    "run_aggregate_scores",
                    "campaign_system_prompt",
                    "skill_file",
                    "eval_cases_file",
                    "reflection_llm_context",
                    "parameters",
                ],
                outputs="proposal_outputs",
                name="build_reflection_proposal",
            ),
            node(
                split_proposal_outputs,
                "proposal_outputs",
                [
                    "proposal_bundle",
                    "proposal_summary_md",
                    "proposal_new_prompt",
                    "proposal_new_skill",
                    "proposal_new_eval_cases",
                    "proposal_prompt_diff",
                    "proposal_skill_diff",
                ],
                name="split_proposal_outputs",
            ),
        ]
    )
