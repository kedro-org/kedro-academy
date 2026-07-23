"""
This is a boilerplate pipeline 'graph_construction'
generated using Kedro 1.4.0
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import build_knowledge_graph, render_graph_html


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(
            func=build_knowledge_graph,
            inputs=["cleaned_healthcare_data", "params:node_colors"],
            outputs="knowledge_graph",
            name="build_knowledge_graph_node",
        ),
        node(
            func=render_graph_html,
            inputs=["knowledge_graph", "entity_summaries", "params:graph_html_path"],
            outputs="graph_metadata",
            name="render_graph_html_node",
        ),
    ])
