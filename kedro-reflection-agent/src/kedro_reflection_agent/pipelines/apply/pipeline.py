"""``apply`` pipeline factory.

Commits an approved reflection proposal to the live locations:
    proposed_prompt      → system_prompt  (new Langfuse version)
    proposed_skill       → skill_text     (overwrites disk)
    proposed_eval_cases  → eval_cases     (appended to Langfuse dataset)
    audit row            → apply_history  (append-only JSON)

Topology:
    commit_reflection(proposed_prompt, proposed_skill, proposed_eval_cases,
                      reflection_id)
        -> system_prompt, skill_text, eval_cases, apply_history
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import commit_reflection


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=commit_reflection,
                inputs=[
                    "proposed_prompt",
                    "proposed_skill",
                    "proposed_eval_cases",
                    "params:reflection_id",
                ],
                outputs=[
                    "system_prompt",
                    "skill_text",
                    "eval_cases",
                    "apply_history",
                ],
                name="commit_reflection_node",
            ),
        ]
    )
