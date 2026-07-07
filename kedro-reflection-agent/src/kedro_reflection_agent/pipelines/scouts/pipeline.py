"""``scouts`` pipeline factory.

Runs all Pattern Scouts against the current run's evaluation outputs and
produces a ``signals.json`` file.  Also updates the rolling cross-agent signal
index (``data/outputs/signal_index.json``) as a side effect inside the node.

Inputs (from other pipeline outputs / catalog):
    - per_case_scores   : catalog_evaluation.yml
    - aggregate_scores  : catalog_evaluation.yml
    - eval_cases        : catalog_evaluation.yml  (DatasetClient, for rubric lookups via .items)
    - params:run_id
    - params:agent_id
    - params:scout_*    (all scout thresholds from parameters.yml)

Outputs:
    - signals           : catalog_scouts.yml → data/outputs/runs/{run_id}/signals.json
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import run_scouts


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=run_scouts,
                inputs=[
                    "per_case_scores",
                    "aggregate_scores",
                    "eval_cases",
                    "params:run_id",
                    "params:agent_id",
                    "params:scout_pass_rate_floor",
                    "params:scout_regression_delta_medium",
                    "params:scout_regression_delta_high",
                    "params:scout_regression_window",
                    "params:scout_rubric_miss_min_cases",
                    "params:scout_hallucination_min_cases",
                    "params:scout_tone_floor",
                    "params:scout_tone_min_cases",
                    "params:scout_cross_unit_min_agents",
                    "params:scout_cross_unit_window",
                ],
                outputs="signals",
                name="run_scouts_node",
            ),
        ]
    )
