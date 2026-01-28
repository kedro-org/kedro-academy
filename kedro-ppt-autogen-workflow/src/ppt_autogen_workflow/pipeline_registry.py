"""Project pipelines registry with namespace support."""

from __future__ import annotations

from kedro.pipeline import Pipeline

from ppt_autogen_workflow.pipelines.preprocessing import create_pipeline as create_preprocessing_pipeline
from ppt_autogen_workflow.pipelines.postprocessing import create_pipeline as create_postprocessing_pipeline
from ppt_autogen_workflow.pipelines.sa_slide_generation_autogen import create_pipeline as create_sa_pipeline
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen import create_pipeline as create_ma_pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines with namespace support.

    Pipeline structure:
    - Shared preprocessing (2 nodes): parse_slide_instructions → extract_slide_objectives → base_slides
    - SA agent pipeline (3 nodes): prepare_sa_slides → llm_context → run_ppt_agent
    - MA agent pipeline (6 nodes): prepare_ma_slides → 4x llm_context → orchestrate_agents
    - Shared postprocessing (1 node): assemble_presentation

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.

    Available pipelines:
        - "__default__": Combined SA + MA pipelines (properly namespaced for --namespace filtering)
        - "preprocessing": Shared preprocessing (2 nodes, outputs base_slides)
        - "postprocessing": Postprocessing base (reused with namespaces)
        - "sa_slide_generation_autogen": Full SA pipeline (6 nodes)
        - "ma_slide_generation_autogen": Full MA pipeline (9 nodes)
    """
    # Get base pipelines
    base_preprocessing = create_preprocessing_pipeline()
    base_postprocessing = create_postprocessing_pipeline()
    sa_agent_pipeline = create_sa_pipeline()
    ma_agent_pipeline = create_ma_pipeline()

    # Create namespaced preprocessing pipelines (shared logic, outputs base_slides)
    preprocessing_sa = Pipeline(
        base_preprocessing,
        namespace="sa",
        outputs={"base_slides": "sa.base_slides"},
    )
    preprocessing_ma = Pipeline(
        base_preprocessing,
        namespace="ma",
        outputs={"base_slides": "ma.base_slides"},
    )

    # Create namespaced postprocessing pipelines
    postprocessing_sa = Pipeline(
        base_postprocessing,
        namespace="sa",
        inputs={"slide_content": "sa.slide_content"},
        outputs={"presentation": "sa.sales_analysis"},
        parameters={"params:layout": "params:layout", "params:styling": "params:styling"},
    )
    postprocessing_ma = Pipeline(
        base_postprocessing,
        namespace="ma",
        inputs={"slide_content": "ma.slide_content"},
        outputs={"presentation": "ma.sales_analysis"},
        parameters={"params:layout": "params:layout", "params:styling": "params:styling"},
    )

    # Combined pipelines (preprocessing + agent + postprocessing)
    combined_sa = preprocessing_sa + sa_agent_pipeline + postprocessing_sa
    combined_ma = preprocessing_ma + ma_agent_pipeline + postprocessing_ma

    return {
        "__default__": combined_sa + combined_ma,
        "preprocessing": base_preprocessing,
        "postprocessing": base_postprocessing,
        "sa_slide_generation_autogen": combined_sa,
        "ma_slide_generation_autogen": combined_ma,
    }