"""Multi-agent AutoGen pipeline."""

from kedro.pipeline import Pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from .nodes import prepare_ma_slides, orchestrate_multi_agent_workflow
from ppt_autogen_workflow.base.tools import (
    build_data_analysis_tools,
    build_chart_generator_tools,
    build_summarizer_tools,
    build_critic_tools,
)


def create_pipeline() -> Pipeline:
    """Create the multi-agent AutoGen pipeline.

    Includes prepare_ma_slides node for agent-specific input formatting.
    """
    return Pipeline([
        node(
            func=prepare_ma_slides,
            inputs="base_slides",
            outputs="slide_configs",
            name="ma_prepare_slides",
        ),
        llm_context_node(
            outputs="planner_context",
            llm="llm_autogen",
            prompts=[
                "planner_system_prompt",
                "planner_user_prompt",
            ],
            tools=[tool(build_data_analysis_tools, "sales_data")],
            name="ma_create_planner_context",
        ),
        llm_context_node(
            outputs="chart_context",
            llm="llm_autogen",
            prompts=[
                "chart_generator_system_prompt",
                "chart_generator_user_prompt",
            ],
            tools=[tool(build_chart_generator_tools, "sales_data", "params:styling")],
            name="ma_create_chart_context",
        ),
        llm_context_node(
            outputs="summarizer_context",
            llm="llm_autogen",
            prompts=[
                "summarizer_system_prompt",
                "summarizer_user_prompt",
            ],
            tools=[tool(build_summarizer_tools, "sales_data")],
            name="ma_create_summarizer_context",
        ),
        llm_context_node(
            outputs="critic_context",
            llm="llm_autogen",
            prompts=[
                "critic_system_prompt",
                "critic_user_prompt",
            ],
            tools=[tool(build_critic_tools)],
            name="ma_create_critic_context",
        ),
        node(
            func=orchestrate_multi_agent_workflow,
            inputs=[
                "planner_context",
                "chart_context",
                "summarizer_context",
                "critic_context",
                "slide_configs",
                "params:quality_assurance",
            ],
            outputs="slide_content",
            name="ma_orchestrate_agents",
        ),
    ], namespace="ma", parameters={"params:quality_assurance": "params:quality_assurance", "params:styling": "params:styling"})
