"""Single-agent AutoGen pipeline"""

from kedro.pipeline import Pipeline, pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from .nodes import run_ppt_agent

# Import shared tool builder from base
from ppt_autogen_workflow.base.tools import build_sa_tools


def create_pipeline() -> Pipeline:
    """Create the single-agent AutoGen pipeline.
    
    Note: Preprocessing and postprocessing are handled by separate pipelines.
    This pipeline expects sa_slide_configs to be available from preprocessing
    and produces sa_slide_content for postprocessing.
    """
    return Pipeline([
        # Step 1: Create LLM context
        # Single agent gets all tools bundled together
        llm_context_node(
            outputs="ppt_llm_context",
            llm="llm_autogen",
            prompts=[
                "ppt_generator_system_prompt",
                "ppt_generator_user_prompt",
            ],
            tools=[tool(build_sa_tools, "sales_data", "params:styling")],
            name="sa_create_ppt_context",
        ),

        # Step 2: Run single agent
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
