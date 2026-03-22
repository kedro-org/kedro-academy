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
                inputs=["opik_judge_llm", "opik_llm_judge_evaluator_prompt"],
                outputs="opik_llm_judge_evaluator",
                name="opik_init_llm_judge_evaluator_node",
            ),
            node(
                func=make_support_task,
                inputs=[
                    "opik_support_answer_prompt",
                    "opik_support_answer_llm",
                    "opik_client",
                ],
                outputs="opik_support_task",
                name="opik_make_support_task_node",
            ),
            node(
                func=run_experiment,
                inputs=[
                    "opik_eval_ds",
                    "opik_support_task",
                    "opik_llm_judge_evaluator",
                    "opik_support_answer_prompt",
                    "params:model_name",
                ],
                outputs=None,
                name="opik_run_experiment_node",
            ),
        ]
    )
