"""Project pipelines registry with namespace support."""

from __future__ import annotations

from kedro.pipeline import Pipeline

from ppt_autogen_workflow.pipelines.preprocessing import create_pipeline as create_preprocessing_pipeline
from ppt_autogen_workflow.pipelines.postprocessing import create_pipeline as create_postprocessing_pipeline
from ppt_autogen_workflow.pipelines.sa_slide_generation_autogen import create_pipeline as create_sa_pipeline
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen import create_pipeline as create_ma_pipeline
from kedro.framework.project import find_pipelines


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines with namespace support.
    
    This function demonstrates how to use Kedro namespaces to reduce duplication:
    1. Base pipelines are created with generic input/output names
    2. Namespaced versions are created by reusing base pipelines with different mappings
    3. This allows the same logic to be reused for MA and SA pipelines
    
    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    
    Available pipelines:
        - "__default__": Full MA pipeline (preprocessing + agent + postprocessing)
        - "preprocessing": Preprocessing for both MA and SA
        - "postprocessing": Postprocessing base (reused with namespaces)
        - "postprocessing_ma": Postprocessing for MA (namespaced)
        - "postprocessing_sa": Postprocessing for SA (namespaced)
        - "sa_slide_generation_autogen": Full SA pipeline
        - "ma_slide_generation_autogen": Full MA pipeline
    """
    pipelines = find_pipelines()
    pipelines["__default__"] = sum(pipelines.values())

    # Get base pipelines
    base_preprocessing = create_preprocessing_pipeline()
    base_postprocessing = create_postprocessing_pipeline()
    sa_agent_pipeline = create_sa_pipeline()
    ma_agent_pipeline = create_ma_pipeline()
    
    # Create namespaced pre-and postprocessing pipelines by reusing the base

    preprocessing_sa = Pipeline(base_preprocessing, namespace="sa", outputs={"slide_configs": "sa.slide_configs"})
    preprocessing_ma = Pipeline(base_preprocessing, namespace="ma", outputs={"slide_configs": "ma.slide_configs"})
    
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
        "preprocessing": base_preprocessing,
        "postprocessing": base_postprocessing,
        "sa_slide_generation_autogen": combined_sa,
        "ma_slide_generation_autogen": combined_ma,
    }