from kedro.pipeline import Pipeline, node, pipeline

from .nodes import apply_prompt_and_skill, merge_eval_dataset


def create_pipeline(**_kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                apply_prompt_and_skill,
                ["proposal_new_prompt", "proposal_new_skill"],
                ["campaign_prompt", "campaign_system_prompt", "skill_file", "campaign_system_prompt_history"],
                name="apply_prompt_and_skill",
            ),
            node(
                merge_eval_dataset,
                inputs=[
                    "eval_cases_file",
                    "proposal_new_eval_cases",
                    "proposal_bundle",
                    "proposal_new_skill",
                    "parameters",
                ],
                outputs=["eval_dataset", "applied_marker"],
                name="merge_eval_dataset",
            ),
        ]
    )
