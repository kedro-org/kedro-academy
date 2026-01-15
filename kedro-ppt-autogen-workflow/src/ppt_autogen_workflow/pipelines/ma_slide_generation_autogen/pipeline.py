"""Multi-agent AutoGen pipeline."""

from kedro.pipeline import Pipeline, pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from .nodes import orchestrate_multi_agent_workflow

# Import shared tool builders from base
from ppt_autogen_workflow.base.tools import (
    build_data_analysis_tools,
    build_chart_generator_tools,
    build_summarizer_tools,
    build_critic_tools,
)
# Import preprocessing and postprocessing from base
from ppt_autogen_workflow.base.postprocessing import assemble_presentation
from .nodes import parse_ma_slide_requirements


def create_pipeline() -> Pipeline:
    """Create the multi-agent AutoGen pipeline with preprocessing and postprocessing."""
    return pipeline([
        # Preprocessing: Parse slide requirements
        node(
            func=parse_ma_slide_requirements,
            inputs="slide_generation_requirements",
            outputs="ma_slide_configs",
            name="ma_parse_slide_requirements",
            tags=["preprocessing", "deterministic", "requirements_parsing"],
        ),

        # Steps 1-4: Context nodes - Bundle LLM + prompts + tools for each agent
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

        # Step 5: Orchestration node - Run multi-agent workflow
        node(
            func=orchestrate_multi_agent_workflow,
            inputs=[
                "planner_context",
                "chart_context",
                "summarizer_context",
                "critic_context",
                "ma_slide_configs",
                "params:quality_assurance",
            ],
            outputs="ma_slide_content",
            name="ma_orchestrate_agents",
            tags=["ma_autogen", "agentic"],
        ),

        # Postprocessing: Assemble presentation
        node(
            func=assemble_presentation,
            inputs=[
                "ma_slide_content",
                "params:layout",
                "params:styling",
            ],
            outputs="sales_analysis_ma",
            name="ma_assemble_presentation",
            tags=["postprocessing", "deterministic", "presentation_assembly"],
        ),
    ])
