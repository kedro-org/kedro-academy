"""Planner Agent for multi-agent PPT generation pipeline.

This module contains the PlannerAgent class responsible for orchestrating
and planning the presentation workflow.
"""
from __future__ import annotations

from ppt_autogen_workflow.base import BaseAgent, PlanOutput


class PlannerAgent(BaseAgent["PlannerAgent"]):
    """Agent responsible for orchestrating and planning the agentic flow.

    Usage:
        agent = PlannerAgent(llm_context).compile()
        output = await agent.invoke(query)
    """

    agent_name = "PlannerAgent"
    system_prompt_key = "planner_system_prompt"

    async def invoke(self, query: str) -> PlanOutput:
        """Invoke the planner agent to create presentation plan.

        Returns:
            PlanOutput with plan and status
        """
        return await self._run_with_output(query, PlanOutput)
