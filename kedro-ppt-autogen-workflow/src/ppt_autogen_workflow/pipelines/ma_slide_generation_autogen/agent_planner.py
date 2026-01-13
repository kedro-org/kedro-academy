"""Planner Agent for multi-agent PPT generation pipeline.

This module contains the PlannerAgent class responsible for orchestrating
and planning the presentation workflow.
"""
from __future__ import annotations

import logging
from typing import Any

from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent["PlannerAgent"]):
    """Agent responsible for orchestrating and planning the agentic flow."""

    async def invoke(self, query: str) -> dict[str, Any]:
        """Invoke the planner agent to create presentation plan."""
        self._ensure_compiled()

        try:
            result = await self._agent.run(task=query)
            plan_output = {
                "query": query,
                "plan": self._extract_content_from_response(result, "plan"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }
            return plan_output

        except Exception as e:
            logger.error(f"Planner agent failed: {str(e)}")
            return {
                "query": query,
                "plan": {},
                "tools_used": [],
                "success": False,
                "error": str(e),
            }


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
