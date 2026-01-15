"""Multi-agent AutoGen PPT generation pipeline.

This pipeline demonstrates clear separation between:
1. Deterministic data preparation (parse_requirements)
2. LLM context assembly (llm_context_nodes for each agent)
3. Agentic content generation (orchestrate_agents)
4. Deterministic presentation assembly (assemble_presentation)

Pipeline structure (7 nodes):
    1. parse_requirements: Parse YAML requirements (deterministic)
    2-5. llm_context_nodes: Create contexts for planner, chart, summarizer, critic
    6. orchestrate_agents: Run multi-agent workflow (agentic)
    7. assemble_presentation: Create final PowerPoint (deterministic)
"""

from kedro.pipeline import Pipeline, pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from .nodes import parse_requirements, orchestrate_multi_agent_workflow, assemble_presentation

# Import tool builders from new module structure
from .planner import build_planner_tools
from .chart import build_chart_generator_tools
from .summary import build_summarizer_tools
from .critic import build_critic_tools


def create_pipeline(**kwargs) -> Pipeline:
    """Create the multi-agent PPT generation pipeline with planner-driven architecture."""
    return pipeline([
        # Step 1: Parse requirements (deterministic)
        node(
            func=parse_requirements,
            inputs="slide_generation_requirements",
            outputs="ma_slide_configs",
            name="parse_requirements",
            tags=["deterministic", "data_preparation"],
        ),
        # Steps 2-5: Context nodes - Bundle LLM + prompts + tools for each agent
        llm_context_node(
            outputs="planner_context",
            llm="llm_autogen",
            prompts=[
                "planner_system_prompt",
                "planner_user_prompt",
            ],
            tools=[tool(build_planner_tools, "sales_data")],
            name="create_planner_context",
        ),
        llm_context_node(
            outputs="chart_context",
            llm="llm_autogen",
            prompts=[
                "chart_generator_system_prompt",
                "chart_generator_user_prompt",
            ],
            tools=[tool(build_chart_generator_tools, "sales_data")],
            name="create_chart_context",
        ),
        llm_context_node(
            outputs="summarizer_context",
            llm="llm_autogen",
            prompts=[
                "summarizer_system_prompt",
                "summarizer_user_prompt",
            ],
            tools=[tool(build_summarizer_tools, "sales_data")],
            name="create_summarizer_context",
        ),
        llm_context_node(
            outputs="critic_context",
            llm="llm_autogen",
            prompts=[
                "critic_system_prompt",
                "critic_user_prompt",
            ],
            tools=[tool(build_critic_tools)],
            name="create_critic_context",
        ),
        # Step 6: Orchestration node - Run multi-agent workflow (agentic)
        node(
            func=orchestrate_multi_agent_workflow,
            inputs=[
                "planner_context",
                "chart_context",
                "summarizer_context",
                "critic_context",
                "ma_slide_configs",
                "params:styling",
                "params:layout",
                "params:quality_assurance",
            ],
            outputs=["slide_chart_paths", "slide_summaries", "slide_configs"],
            name="orchestrate_agents",
            tags=["autogen", "agentic", "orchestration"],
        ),
        # Step 7: Assembly node - Create final PowerPoint (deterministic)
        node(
            func=assemble_presentation,
            inputs="slide_configs",
            outputs="sales_analysis_ma",
            name="assemble_presentation",
            tags=["deterministic", "assembly"],
        ),
    ])
