from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    init_llm_judge_evaluator,
    make_support_task,
    run_experiment,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=init_llm_judge_evaluator,
                inputs=["judge_llm", "llm_judge_evaluator_prompt"],
                outputs="llm_judge_evaluator",
                name="init_llm_judge_evaluator_node",
            ),
            node(
                func=make_support_task,
                inputs=[
                    "support_answer_prompt",
                    "support_answer_llm",
                    "langfuse_client",
                ],
                outputs="support_task",
                name="make_support_task_node",
            ),
            node(
                func=run_experiment,
                inputs=[
                    "eval_ds",
                    "support_task",
                    "llm_judge_evaluator",
                    "params:support_answer_prompt_version",
                ],
                outputs=None,
                name="run_experiment_node",
            ),
        ]
    )
