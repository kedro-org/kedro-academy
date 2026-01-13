"""Single-agent AutoGen PPT generation pipeline."""

from kedro.pipeline import Pipeline, pipeline, node

from .nodes import init_tools, compile_ppt_agent, generate_presentation


def create_pipeline(**kwargs) -> Pipeline:
    """Create the single-agent AutoGen PPT generation pipeline."""
    return pipeline([
        node(
            func=init_tools,
            inputs=["sales_data"],
            outputs="tools",
            name="init_tools_node",
            tags=["tools"],
        ),
        node(
            func=compile_ppt_agent,
            inputs=[
                "slide_generation_requirements",
                "ppt_generator_system_prompt",
                "ppt_generator_user_prompt",
                "llm_autogen",
                "tools",
            ],
            outputs="compiled_ppt_agent",
            name="compile_ppt_agent",
            tags=["autogen", "compilation", "single_agent"],
        ),
        node(
            func=generate_presentation,
            inputs=["compiled_ppt_agent"],
            outputs="sales_analysis_sa",
            name="generate_presentation",
            tags=["autogen", "generation", "single_agent"],
        ),
    ])
