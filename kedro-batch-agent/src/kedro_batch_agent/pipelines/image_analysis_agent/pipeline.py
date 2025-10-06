"""
This is a boilerplate pipeline 'image_analysis_agent'
generated using Kedro 1.0.0
"""

from kedro.pipeline import Node, Pipeline  # noqa

from experiment.pipelines.image_analysis_agent.nodes import (
    build_graph,
    init_state,
    invoke_graph,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=build_graph,
                inputs=["llm", "image_analysis_prompt"],
                outputs="graph",
            ),
            Node(
                func=init_state,
                inputs=[
                    "claims_pics",
                    "params:max_images",
                    "params:confidence_threshold",
                ],
                outputs="init_state",
            ),
            Node(
                func=invoke_graph,
                inputs=["graph", "init_state"],
                outputs="response_image_analysis",
            ),
        ]
    )
