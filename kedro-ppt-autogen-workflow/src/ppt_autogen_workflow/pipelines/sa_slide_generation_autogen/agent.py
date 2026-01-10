"""Single-agent PPT Generation using AutoGen."""
from __future__ import annotations

import logging
from typing import Any

from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)


class PPTGenerationAgent(BaseAgent["PPTGenerationAgent"]):
    """Agent responsible for generating PowerPoint presentations from sales data."""

    async def invoke(self, query: str) -> dict[str, Any]:
        """Invoke the agent to generate presentation content."""
        self._ensure_compiled()

        try:
            result = await self._agent.run(task=query)
            output = {
                "query": query,
                "content": self._extract_content_from_response(result, "content"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }
            return output

        except Exception as e:
            logger.error(f"PPT generation agent failed: {str(e)}")
            return {
                "query": query,
                "content": {},
                "tools_used": [],
                "success": False,
                "error": str(e),
            }


def create_ppt_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> PPTGenerationAgent:
    """Create a PPT generation agent."""
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="PPTGenerator",
    )
    return PPTGenerationAgent(context).compile()
