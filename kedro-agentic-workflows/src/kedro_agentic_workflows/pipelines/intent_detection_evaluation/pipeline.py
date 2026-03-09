from kedro.pipeline import llm_context_node, node, pipeline, Pipeline

from .nodes import (
    init_llm_judge_evaluator,
    make_intent_agent_task,
    run_experiment,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="intent_agent_context_node",
                outputs="intent_detection_context",
                llm="llm",
                prompts=[
                    "intent_prompt_langfuse",
                ],
            ),
            node(
                func=init_llm_judge_evaluator,
                inputs=[
                    "intent_judge_llm",
                    "intent_llm_judge_evaluator_prompt"
                ],
                outputs="reason_judge_evaluator",
                name="init_intent_llm_judge_evaluator_node",
            ),
            node(
                func=make_intent_agent_task,
                inputs=[
                    "intent_detection_context",
                    "langfuse_client",
                ],
                outputs="intent_agent_task",
                name="make_intent_evaluation_task_node",
            ),
            node(
                func=run_experiment,
                inputs=[
                    "intent_eval_ds",
                    "intent_agent_task",
                    "reason_judge_evaluator",
                    "params:intent_prompt_version",
                ],
                outputs=None,
                name="run_experiment_node",
            ),
        ]
    )
