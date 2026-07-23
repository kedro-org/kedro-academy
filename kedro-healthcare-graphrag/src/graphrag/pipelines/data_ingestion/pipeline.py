"""
This is a boilerplate pipeline 'data_ingestion'
generated using Kedro 1.4.0
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import clean_data, extract_entity_summaries, store_entity_stats


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(
            func=clean_data,
            inputs="raw_healthcare_data",
            outputs="cleaned_healthcare_data",
            name="clean_data_node",
        ),
        node(
            func=extract_entity_summaries,
            inputs="cleaned_healthcare_data",
            outputs="entity_summaries",
            name="extract_entity_summaries_node",
        ),
        node(
            func=store_entity_stats,
            inputs="entity_summaries",
            outputs="entity_stats",
            name="store_entity_stats_node",
        ),
    ])
