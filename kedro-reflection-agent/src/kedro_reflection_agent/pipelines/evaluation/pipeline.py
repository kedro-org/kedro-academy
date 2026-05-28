"""``evaluation`` pipeline factory.

Drives a Langfuse ``DatasetClient.run_experiment(...)`` over the evaluation
dataset. The task is an in-memory lookup of campaign-generated emails for the
given ``run_id``; evaluators are 4 heuristic + 1 combined LLM judge (returns
3 ``Evaluation`` objects).

Topology:
    judge_context_node              -> judge_context  (LLMContext)
    init_heuristic_evaluators(products, body_length_min, body_length_max)
                                    -> heuristic_evaluators  (list[callable])
    init_judge_evaluator(judge_context, customers, products)
                                    -> judge_evaluator  (callable)
    make_campaign_task(run_id)      -> campaign_task  (callable)
    run_experiment(eval_cases, campaign_task, heuristic_evaluators,
                   judge_evaluator, run_id, model_name,
                   system_prompt_version, judge_model_name,
                   judge_prompt_version, passing_threshold)
                                    -> per_case_scores, aggregate_scores
"""

from kedro.pipeline import Pipeline, llm_context_node, node, pipeline

from .nodes import (
    init_heuristic_evaluators,
    init_judge_evaluator,
    make_campaign_task,
    run_experiment,
)


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="judge_context_node",
                outputs="judge_context",
                llm="judge_llm",
                prompts=["judge_prompt"],
            ),
            node(
                func=init_heuristic_evaluators,
                inputs=[
                    "products",
                    "params:body_length_min",
                    "params:body_length_max",
                ],
                outputs="heuristic_evaluators",
                name="init_heuristic_evaluators_node",
            ),
            node(
                func=init_judge_evaluator,
                inputs=["judge_context", "customers", "products", "params:agent_id"],
                outputs="judge_evaluator",
                name="init_judge_evaluator_node",
            ),
            node(
                func=make_campaign_task,
                inputs=["params:run_id", "params:agent_id"],
                outputs="campaign_task",
                name="make_campaign_task_node",
            ),
            node(
                func=run_experiment,
                inputs=[
                    "eval_cases",
                    "campaign_task",
                    "heuristic_evaluators",
                    "judge_evaluator",
                    "params:run_id",
                    "params:agent_id",
                    "params:model_name",
                    "params:system_prompt_version",
                    "params:judge_model_name",
                    "params:judge_prompt_version",
                    "params:passing_threshold",
                ],
                outputs=["per_case_scores", "aggregate_scores"],
                name="run_experiment_node",
            ),
        ]
    )
