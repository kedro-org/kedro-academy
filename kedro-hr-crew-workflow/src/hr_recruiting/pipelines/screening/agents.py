"""Agent classes for screening pipeline.

This module contains all agent classes needed for the screening
orchestration workflow using CrewAI.
"""

from __future__ import annotations
from hr_recruiting.base.agent import BaseAgent



class RequirementsMatcherAgent(BaseAgent["RequirementsMatcherAgent"]):
    """Agent responsible for matching job requirements to candidate evidence.

    Usage:
        agent = RequirementsMatcherAgent(llm_context).compile()
        # Agent is used within CrewAI tasks, not directly invoked
    """

    agent_name = "RequirementsMatcherAgent"
    system_prompt_key = "requirements_matcher_agent_system_prompt"


class ResumeEvaluatorAgent(BaseAgent["ResumeEvaluatorAgent"]):
    """Agent responsible for evaluating candidate qualifications.

    Usage:
        agent = ResumeEvaluatorAgent(llm_context).compile()
        # Agent is used within CrewAI tasks, not directly invoked
    """

    agent_name = "ResumeEvaluatorAgent"
    system_prompt_key = "resume_evaluator_agent_system_prompt"


class CommsDrafterAgent(BaseAgent["CommsDrafterAgent"]):
    """Agent responsible for drafting professional email communications.

    Usage:
        agent = CommsDrafterAgent(llm_context).compile()
        # Agent is used within CrewAI tasks, not directly invoked
    """

    agent_name = "CommsDrafterAgent"
    system_prompt_key = "comms_drafter_agent_system_prompt"
