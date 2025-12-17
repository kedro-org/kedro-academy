"""Multi-agent AutoGen PPT generation pipeline."""

from kedro.pipeline import Pipeline, pipeline, node

from .nodes import (
    initialize_planner_agent,
    initialize_chart_generator_agent,
    initialize_summarizer_agent,
    initialize_critic_agent,
    orchestrate_multi_agent_workflow
)


def create_pipeline(**kwargs) -> Pipeline:
    """
    Create the multi-agent PPT generation pipeline.
    
    Orchestrates 4 specialized agents (Planner, ChartGenerator, Summarizer, Critic)
    to parse instructions_yaml and generate slides with QA review.
    
    Returns:
        Pipeline object with agent initialization and orchestration nodes
    """
    return pipeline([
        # Initialize all specialized agents with sales_data for tool access
        node(
            func=initialize_planner_agent,
            inputs=["llm_autogen", "sales_data"],
            outputs="compiled_planner_agent",
            name="compile_planner_agent",
            tags=["autogen", "compilation", "planner", "multi_agent"],
        ),
        node(
            func=initialize_chart_generator_agent,
            inputs=["llm_autogen", "sales_data"],
            outputs="compiled_chart_agent",
            name="compile_chart_generator_agent",
            tags=["autogen", "compilation", "chart_generator", "multi_agent"],
        ),
        node(
            func=initialize_summarizer_agent,
            inputs=["llm_autogen", "sales_data"],
            outputs="compiled_summarizer_agent",
            name="compile_summarizer_agent",
            tags=["autogen", "compilation", "summarizer", "multi_agent"],
        ),
        node(
            func=initialize_critic_agent,
            inputs=["llm_autogen", "sales_data"],
            outputs="compiled_critic_agent",
            name="compile_critic_agent",
            tags=["autogen", "compilation", "critic", "multi_agent"],
        ),
        # Orchestrate multi-agent workflow
        node(
            func=orchestrate_multi_agent_workflow,
            inputs=[
                "compiled_planner_agent",
                "compiled_chart_agent",
                "compiled_summarizer_agent",
                "compiled_critic_agent",
                "instructions_yaml",
                "sales_data",
                "params:user_query",
            ],
            outputs=["final_presentation", "slide_charts", "slide_summaries"],
            name="orchestrate_agents",
            tags=["autogen", "orchestration", "multi_agent"],
        ),
    ])