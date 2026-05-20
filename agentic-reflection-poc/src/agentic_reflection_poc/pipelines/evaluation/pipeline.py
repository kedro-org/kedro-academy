from kedro.pipeline import Pipeline, llm_context_node, node, pipeline

from .nodes import evaluate_run


def create_pipeline(**_kwargs) -> Pipeline:
    return pipeline(
        [
            llm_context_node(
                name="build_judge_llm_context",
                outputs="judge_llm_context",
                llm="judge_llm",
                prompts=["judge_system_prompt"],
            ),
            node(
                evaluate_run,
                inputs=[
                    "run_emails",
                    "eval_cases_file",
                    "customers",
                    "products",
                    "langfuse_tracer",
                    "judge_llm_context",
                    "parameters",
                ],
                outputs=["run_case_scores", "run_aggregate_scores"],
                name="evaluate_run",
            ),
        ]
    )
