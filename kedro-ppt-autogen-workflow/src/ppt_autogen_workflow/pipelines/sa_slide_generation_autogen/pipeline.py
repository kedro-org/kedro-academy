"""Single-agent AutoGen PPT generation pipeline.

This pipeline uses Kedro's llm_context_node to bundle LLM, prompts, and tools
into an LLMContext object, reducing boilerplate and simplifying the pipeline.
"""

from kedro.pipeline import Pipeline, pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from .nodes import generate_presentation
from .tools import build_tools


def create_pipeline(**kwargs) -> Pipeline:
    """Create the single-agent AutoGen PPT generation pipeline.

    Pipeline structure (2 nodes):
        1. llm_context_node: Bundles LLM + prompts + tools into LLMContext
        2. generate_presentation: Uses LLMContext to create agent and generate slides
    """
    return pipeline([
        llm_context_node(
            outputs="ppt_llm_context",
            llm="llm_autogen",
            prompts=[
                "ppt_generator_system_prompt",
                "ppt_generator_user_prompt",
            ],
            tools=[tool(build_tools, "sales_data")],
            name="create_ppt_context",
        ),
        node(
            func=generate_presentation,
            inputs=[
                "ppt_llm_context",
                "slide_generation_requirements",
            ],
            outputs="sales_analysis_sa",
            name="generate_presentation",
            tags=["autogen", "generation", "single_agent"],
        ),
    ])
