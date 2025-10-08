"""
This is a boilerplate pipeline 'completion_agent'
generated using Kedro 1.0.0
"""

from kedro.pipeline import Node, Pipeline  # noqa

from experiment.pipelines.completion_agent.nodes import (
    create_agent,
    generate_response,
    init_tools,
)


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=init_tools,
                inputs="claims_docs",
                outputs="tools",
            ),
            Node(
                func=create_agent,
                inputs=["llm", "tools", "claim_completion_prompt"],
                outputs="agent",
            ),
            Node(func=generate_response, inputs="agent", outputs="response_completion"),
        ]
    )
