"""Graph update pipeline — merges a new data batch into the existing knowledge graph."""
from kedro.pipeline import Pipeline, node, pipeline

from graphrag.pipelines.graph_construction.nodes import render_graph_html, update_knowledge_graph


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(
            func=update_knowledge_graph,
            inputs=[
                "existing_knowledge_graph",
                "cleaned_healthcare_data",
                "params:node_colors",
                "params:update_batch_size",
            ],
            outputs="knowledge_graph",
            name="update_knowledge_graph_node",
        ),
        node(
            func=render_graph_html,
            inputs=["knowledge_graph", "entity_summaries", "params:graph_html_path"],
            outputs="updated_graph_metadata",
            name="render_updated_graph_html_node",
        ),
    ])
