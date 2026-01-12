"""Multi-agent AutoGen PPT generation pipeline."""

from kedro.pipeline import Pipeline, pipeline, node

from .nodes import (
    init_tools,
    analyze_requirements,
    compile_planner_agent,
    compile_chart_generator_agent,
    compile_summarizer_agent,
    compile_critic_agent,
    orchestrate_multi_agent_workflow
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the multi-agent PPT generation pipeline with planner-driven architecture."""
    return pipeline([
        node(
            func=init_tools,
            inputs=["sales_data"],
            outputs="tools",
            name="init_tools_node",
            tags=["tools"],
        ),
        node(
            func=analyze_requirements,
            inputs=[
                "slide_generation_requirements",
                "params:styling",
                "params:layout",
            ],
            outputs=["planner_requirements", "chart_requirements", "summarizer_requirements"],
            name="analyze_requirements",
            tags=["analysis", "requirements"],
        ),
        node(
            func=compile_planner_agent,
            inputs=[
                "planner_requirements",
                "planner_system_prompt",
                "planner_user_prompt",
                "llm_autogen",
                "tools",
            ],
            outputs="compiled_planner_agent",
            name="compile_planner_agent",
            tags=["autogen", "compilation", "planner"],
        ),
        node(
            func=compile_chart_generator_agent,
            inputs=[
                "chart_requirements",
                "chart_generator_system_prompt",
                "chart_generator_user_prompt",
                "llm_autogen",
                "tools",
            ],
            outputs="compiled_chart_agent",
            name="compile_chart_generator_agent",
            tags=["autogen", "compilation", "chart_generator"],
        ),
        node(
            func=compile_summarizer_agent,
            inputs=[
                "summarizer_requirements",
                "summarizer_system_prompt",
                "summarizer_user_prompt",
                "llm_autogen",
                "tools",
            ],
            outputs="compiled_summarizer_agent",
            name="compile_summarizer_agent",
            tags=["autogen", "compilation", "summarizer"],
        ),
        node(
            func=compile_critic_agent,
            inputs=[
                "critic_system_prompt",
                "critic_user_prompt",
                "params:quality_assurance",
                "llm_autogen",
                "tools",
            ],
            outputs="compiled_critic_agent",
            name="compile_critic_agent",
            tags=["autogen", "compilation", "critic"],
        ),
        node(
            func=orchestrate_multi_agent_workflow,
            inputs=[
                "compiled_planner_agent",
                "compiled_chart_agent",
                "compiled_summarizer_agent",
                "compiled_critic_agent",
            ],
            outputs=["sales_analysis_ma", "slide_charts", "slide_summaries"],
            name="orchestrate_agents",
            tags=["autogen", "orchestration"],
        ),
    ])