"""Project pipelines registry."""
from __future__ import annotations

from kedro.pipeline import Pipeline

from ppt_autogen_workflow.pipelines.sa_slide_generation_autogen import create_pipeline as create_sa_pipeline
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen import create_pipeline as create_ma_pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """
    Register the project's pipelines.

    Returns:
        A mapping from pipeline names to Pipeline objects.

    Available pipelines:
        - "__default__": Multi-agent slide generation pipeline
        - "sa_slide_generation_autogen": Single-agent PPT generation pipeline
        - "ma_slide_generation_autogen": Multi-agent orchestrated workflow pipeline
    
    Usage:
        kedro run                                        # Run the multi-agent pipeline (default)
        kedro run --pipeline=sa_slide_generation_autogen     # Single agent version
        kedro run --pipeline=ma_slide_generation_autogen     # Multi-agent orchestrated workflow
    """
    # Single-agent PPT generation pipeline
    single_agent_pipeline = create_sa_pipeline()
    
    # Multi-agent orchestrated workflow pipeline
    multi_agent_pipeline = create_ma_pipeline()

    return {
        "__default__": multi_agent_pipeline,  # Use multi-agent as default
        "sa_slide_generation_autogen": single_agent_pipeline,
        "ma_slide_generation_autogen": multi_agent_pipeline,
    }
