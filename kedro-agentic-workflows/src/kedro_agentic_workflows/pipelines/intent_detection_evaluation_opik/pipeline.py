from kedro.pipeline import llm_context_node, node, pipeline, Pipeline

from .nodes import (
    init_intent_accuracy_evaluator,
    init_reason_judge_evaluator,
    make_intent_detection_task,
    run_experiment,
)


def create_pipeline(**kwargs) -> Pipeline:
    # Opik variant of the intent-detection evaluation pipeline. It mirrors the
    # Langfuse pipeline (intent_detection_evaluation) and uses the same generic
    # dataset names, bound to Opik datasets in conf/opik/. Run with `--env opik`.
    return pipeline(
        [
            llm_context_node(
                name="opik_intent_agent_context_node",
                outputs="intent_detection_context",
                llm="llm",
                prompts=["intent_prompt"],
            ),
            node(
                func=init_intent_accuracy_evaluator,
                inputs=None,
                outputs="intent_accuracy_evaluator",
                name="opik_init_intent_accuracy_evaluator_node",
            ),
            node(
                func=init_reason_judge_evaluator,
                inputs=[
                    "intent_judge_llm",
                    "intent_judge_prompt",
                ],
                outputs="reason_judge_evaluator",
                name="opik_init_reason_judge_evaluator_node",
            ),
            node(
                func=make_intent_detection_task,
                inputs=[
                    "intent_detection_context",
                    "opik_client",
                ],
                outputs="intent_agent_task",
                name="opik_make_intent_detection_task_node",
            ),
            node(
                func=run_experiment,
                inputs=[
                    "intent_evaluation_data",
                    "intent_agent_task",
                    "intent_accuracy_evaluator",
                    "reason_judge_evaluator",
                    "params:intent_prompt_version",
                    "params:model_name",
                ],
                outputs=None,
                name="opik_run_intent_experiment_node",
            ),
        ]
    )
