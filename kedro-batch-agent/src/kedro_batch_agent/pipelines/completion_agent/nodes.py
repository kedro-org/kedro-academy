from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from .data_models import Claim


def list_files_tool(claims_docs):
    """Create tool to list all available documents"""

    @tool
    def list_files():
        """List files available to read"""
        return list(claims_docs.keys())

    return list_files


def load_text_tool(claims_docs):
    """Create tool to load text content of a specific claims document."""

    @tool
    def load_text(file_name):
        """Load text content of a specific claims document."""
        return claims_docs[file_name]()

    return load_text


def init_tools(claim_docs):
    """Bind tools to PartitionedDataset for the agent to use"""
    return {
        "list_files": list_files_tool(claim_docs),
        "load_text": load_text_tool(claim_docs),
    }


def create_agent(llm, tools, prompt, response_format=Claim):
    """Create a React agent with the specified tools and prompt."""
    agent = create_react_agent(
        model=llm,
        tools=list(tools.values()),
        prompt=prompt,
        response_format=response_format,
    )
    return agent


def generate_response(agent):
    """Invoke the agent to generate a structured response."""
    response = agent.invoke({"input": "Extract information from available documents"})
    return response["structured_response"].model_dump()
