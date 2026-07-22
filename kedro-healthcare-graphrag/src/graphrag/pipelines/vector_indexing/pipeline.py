"""
This is a boilerplate pipeline 'vector_indexing'
generated using Kedro 1.4.0
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import create_rag_documents, embed_documents


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(
            func=create_rag_documents,
            inputs=["entity_summaries", "knowledge_graph"],
            outputs="rag_documents",
            name="create_rag_documents_node",
        ),
        node(
            func=embed_documents,
            inputs=["rag_documents", "params:embedding_model"],
            outputs="chroma_collection",
            name="embed_documents_node",
        ),
    ])
