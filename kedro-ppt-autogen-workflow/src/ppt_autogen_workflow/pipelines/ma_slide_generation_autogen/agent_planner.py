"""Planner Agent for multi-agent PPT generation pipeline.

This module contains the PlannerAgent class responsible for orchestrating
and planning the presentation workflow.
"""
from __future__ import annotations

import logging

from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent, PlanOutput

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent["PlannerAgent"]):
    """Agent responsible for orchestrating and planning the agentic flow."""

    async def invoke(self, query: str) -> PlanOutput:
        """Invoke the planner agent to create presentation plan.

        Returns:
            PlanOutput with plan and status
        """
        return await self._run_with_output(query, PlanOutput)


def create_planner_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> PlannerAgent:
    """Create a planner agent for orchestrating presentation workflow."""
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="PlannerAgent",
    )
    return PlannerAgent(context).compile()
