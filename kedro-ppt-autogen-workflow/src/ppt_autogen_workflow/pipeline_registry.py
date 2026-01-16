"""Project pipelines registry with namespace support."""

from __future__ import annotations

from kedro.pipeline import Pipeline
from kedro.framework.project import find_pipelines

from ppt_autogen_workflow.pipelines.preprocessing import (
    create_sa_preprocessing_pipeline,
    create_ma_preprocessing_pipeline,
)
from ppt_autogen_workflow.pipelines.postprocessing import create_pipeline as create_postprocessing_pipeline
from ppt_autogen_workflow.pipelines.sa_slide_generation_autogen import create_pipeline as create_sa_pipeline
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen import create_pipeline as create_ma_pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines with namespace support.

    Preprocessing pipelines have 3 nodes each (per Elena's review):
    1. parse_slide_instructions - Parse raw YAML
    2. extract_slide_objectives - Extract common objectives
    3. prepare_sa_slides / prepare_ma_slides - Pipeline-specific preparation

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.

    Available pipelines:
        - "__default__": All discovered pipelines combined
        - "preprocessing_sa": SA preprocessing (3 nodes)
        - "preprocessing_ma": MA preprocessing (3 nodes)
        - "postprocessing": Postprocessing base (reused with namespaces)
        - "sa_slide_generation_autogen": Full SA pipeline
        - "ma_slide_generation_autogen": Full MA pipeline
    """
    pipelines = find_pipelines()
    pipelines["__default__"] = sum(pipelines.values())

    # Get base pipelines
    sa_preprocessing = create_sa_preprocessing_pipeline()
    ma_preprocessing = create_ma_preprocessing_pipeline()
    base_postprocessing = create_postprocessing_pipeline()
    sa_agent_pipeline = create_sa_pipeline()
    ma_agent_pipeline = create_ma_pipeline()

    # Create namespaced preprocessing pipelines
    preprocessing_sa = Pipeline(sa_preprocessing, namespace="sa", outputs={"slide_configs": "sa.slide_configs"})
    preprocessing_ma = Pipeline(ma_preprocessing, namespace="ma", outputs={"slide_configs": "ma.slide_configs"})
    
    postprocessing_ma = Pipeline(
        base_postprocessing,
        namespace="ma",
        inputs={"slide_content": "ma.slide_content"},  # Map generic input to MA-specific
        outputs={"presentation": "ma.sales_analysis"},  # Map generic output to MA-specific
        parameters={"params:layout": "params:layout", "params:styling": "params:styling"}
    )
    
    postprocessing_sa = Pipeline(
        base_postprocessing,
        namespace="sa",
        inputs={"slide_content": "sa.slide_content"},  # Map generic input to SA-specific
        outputs={"presentation": "sa.sales_analysis"},  # Map generic output to SA-specific
        parameters={"params:layout": "params:layout", "params:styling": "params:styling"}
    )
    
    # Combined pipelines
    combined_ma = preprocessing_ma + ma_agent_pipeline + postprocessing_ma
    combined_sa = preprocessing_sa + sa_agent_pipeline + postprocessing_sa
    
    return {
        "__default__": pipelines["__default__"],
        "preprocessing_sa": sa_preprocessing,
        "preprocessing_ma": ma_preprocessing,
        "postprocessing": base_postprocessing,
        "sa_slide_generation_autogen": combined_sa,
        "ma_slide_generation_autogen": combined_ma,
    }