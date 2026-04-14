from kedro.pipeline import llm_context_node, node, pipeline, Pipeline

from .nodes import (
    init_intent_accuracy_evaluator,
    init_reason_judge_evaluator,
    make_intent_detection_task,
    run_experiment,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="opik_intent_agent_context_node",
                outputs="opik_intent_detection_context",
                llm="llm",
                prompts=["intent_prompt"],
            ),
            node(
                func=init_intent_accuracy_evaluator,
                inputs=None,
                outputs="opik_intent_accuracy_evaluator",
                name="opik_init_intent_accuracy_evaluator_node",
            ),
            node(
                func=init_reason_judge_evaluator,
                inputs=[
                    "opik_intent_judge_llm",
                    "opik_intent_judge_prompt",
                ],
                outputs="opik_reason_judge_evaluator",
                name="opik_init_reason_judge_evaluator_node",
            ),
            node(
                func=make_intent_detection_task,
                inputs=[
                    "opik_intent_detection_context",
                    "opik_client",
                ],
                outputs="opik_intent_agent_task",
                name="opik_make_intent_detection_task_node",
            ),
            node(
                func=run_experiment,
                inputs=[
                    "opik_intent_evaluation_data",
                    "opik_intent_agent_task",
                    "opik_intent_accuracy_evaluator",
                    "opik_reason_judge_evaluator",
                    "opik_intent_judge_prompt",
                    "params:model_name",
                ],
                outputs=None,
                name="opik_run_intent_experiment_node",
            ),
        ]
    )
