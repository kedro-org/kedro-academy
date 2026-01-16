"""Preprocessing pipeline for parsing slide generation requirements."""

from kedro.pipeline import Pipeline, node

from .nodes import parse_slide_requirements


# Base pipeline that can be reused with namespaces
# Note: This uses parse_slide_requirements which accepts pipeline_type parameter
# In the registry, we'll create namespaced versions with different parameters
_base_parse_pipeline = Pipeline([
    node(
        func=parse_slide_requirements,
        inputs="slide_generation_requirements",
        outputs="slide_configs",  # Generic output name
        name="parse_slide_requirements",
        # pipeline_type will be passed via parameters in namespaced versions
    ),
])


def create_pipeline(**kwargs) -> Pipeline:
    """Create the preprocessing pipeline.
    
    This pipeline parses slide generation requirements.
    Returns a base pipeline that should be reused with namespaces in the registry.
    
    Note: To use namespaces effectively, create namespaced versions in the registry:
    - MA version: namespace="ma", outputs={"slide_configs": "ma_slide_configs"}, 
                  parameters={"params:pipeline_type": "ma"} (if using params)
    - SA version: namespace="sa", outputs={"slide_configs": "sa_slide_configs"},
                  parameters={"params:pipeline_type": "sa"} (if using params)
    
    However, since parse_slide_requirements uses a function parameter (not params),
    we need to use wrapper functions. See pipeline_registry.py for namespace examples.
    
    Returns:
        Base pipeline that processes slide_generation_requirements into slide_configs
    """
    return _base_parse_pipeline
