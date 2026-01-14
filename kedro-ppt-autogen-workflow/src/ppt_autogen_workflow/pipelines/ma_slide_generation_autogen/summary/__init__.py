"""Summary module for summarizer agent and utilities.

This module contains the SummarizerAgent and all related summary
generation logic, keeping everything traceable in one place.
"""
from .agent import SummarizerAgent, create_summarizer_agent, generate_summary
from .generator import analyze_dataframe, generate_summary_text
from .tools import build_summarizer_tools

__all__ = [
    "SummarizerAgent",
    "create_summarizer_agent",
    "generate_summary",
    "analyze_dataframe",
    "generate_summary_text",
    "build_summarizer_tools",
]
