"""Critic module for critic agent and QA utilities.

This module contains the CriticAgent responsible for quality
assurance and review of generated slide content.
"""
from .agent import CriticAgent, create_critic_agent, run_qa_review
from .tools import build_critic_tools

__all__ = [
    "CriticAgent",
    "create_critic_agent",
    "run_qa_review",
    "build_critic_tools",
]
