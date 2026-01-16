"""Postprocessing pipeline for assembling PowerPoint presentations."""

from kedro.pipeline import Pipeline, node

from .nodes import assemble_presentation


# Base pipeline that can be reused with namespaces
# This base pipeline uses generic input/output names that will be mapped
# to specific names when reused in the registry
_base_assembly_pipeline = Pipeline([
    node(
        func=assemble_presentation,
        inputs=[
            "slide_content",  # Generic input - will be mapped to ma_slide_content or sa_slide_content
            "params:layout",
            "params:styling",
        ],
        outputs="presentation",  # Generic output - will be mapped to sales_analysis_ma or sales_analysis_sa
        name="assemble_presentation",
    ),
])


def create_pipeline(**kwargs) -> Pipeline:
    """Create the postprocessing pipeline.
    
    This pipeline assembles presentations from agent-generated slide content.
    Returns a base pipeline that should be reused with namespaces in the registry.
    
    The base pipeline will be reused twice:
    1. With namespace="ma", mapping slide_content -> ma_slide_content, presentation -> sales_analysis_ma
    2. With namespace="sa", mapping slide_content -> sa_slide_content, presentation -> sales_analysis_sa
    
    Returns:
        Base pipeline that processes slide content into final presentations
    """
    return _base_assembly_pipeline
