"""Single-agent AutoGen pipeline."""

from kedro.pipeline import Pipeline, pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from .nodes import prepare_sa_slides, run_ppt_agent
from ppt_autogen_workflow.base.tools import build_sa_tools


def create_pipeline() -> Pipeline:
    """Create the single-agent AutoGen pipeline.

    Includes prepare_sa_slides node for input formatting.
    """
    return Pipeline([
        node(
            func=prepare_sa_slides,
            inputs="base_slides",
            outputs="slide_configs",
            name="sa_prepare_slides",
            tags=["sa", "deterministic"],
        ),
        llm_context_node(
            outputs="ppt_llm_context",
            llm="llm_autogen",
            prompts=[
                "ppt_generator_system_prompt",
                "ppt_generator_user_prompt",
                "chart_generator_user_prompt",
                "summary_generator_user_prompt",
            ],
            tools=[tool(build_sa_tools, "sales_data", "params:styling")],
            name="sa_create_ppt_context",
        ),
        node(
            func=run_ppt_agent,
            inputs=[
                "ppt_llm_context",
                "slide_configs",
            ],
            outputs="slide_content",
            name="sa_run_ppt_agent",
            tags=["sa"],
        ),
    ], namespace="sa", parameters={"params:styling": "params:styling"})
