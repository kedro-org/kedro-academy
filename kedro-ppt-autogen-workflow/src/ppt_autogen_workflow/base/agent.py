"""Base agent classes for AutoGen integration.

This module provides shared base classes for all AutoGen agents in the project.
Both single-agent and multi-agent pipelines can inherit from BaseAgent to
eliminate code duplication.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

logger = logging.getLogger(__name__)

# Type variable for generic agent typing
T = TypeVar("T", bound="BaseAgent")


@dataclass
class AgentContext:
    """Configuration context for AutoGen agents.

    Attributes:
        model_client: The OpenAI chat completion client for LLM calls
        tools: List of tools available to the agent
        system_prompt: The system message defining agent behavior
        agent_name: Unique identifier for the agent
    """
    model_client: OpenAIChatCompletionClient
    tools: list[Any] = field(default_factory=list)
    system_prompt: str = ""
    agent_name: str = "Agent"


class BaseAgent(ABC, Generic[T]):
    """Base class for all AutoGen agents with shared functionality.

    This abstract base class provides common implementation for:
    - Agent initialization and compilation
    - Tool usage extraction from responses
    - Content extraction from agent messages

    Subclasses only need to implement the invoke() method with their
    specific logic and output structure.

    Example:
        ```python
        class MyAgent(BaseAgent["MyAgent"]):
            async def invoke(self, task: str) -> dict[str, Any]:
                self._ensure_compiled()
                result = await self._agent.run(task=task)
                return {
                    "content": self._extract_content_from_response(result),
                    "tools_used": self._extract_tools_used(result),
                }
        ```
    """

    def __init__(self, context: AgentContext) -> None:
        """Initialize the agent with configuration context.

        Args:
            context: AgentContext containing model client, tools, and prompts
        """
        self.context = context
        self._agent: AssistantAgent | None = None

    def compile(self: T) -> T:
        """Compile and initialize the AutoGen AssistantAgent.

        Creates the underlying AutoGen AssistantAgent with the configured
        model client, tools, and system prompt.

        Returns:
            Self for method chaining
        """
        logger.info(f"Compiling {self.context.agent_name} agent...")

        self._agent = AssistantAgent(
            name=self.context.agent_name,
            model_client=self.context.model_client,
            tools=self.context.tools,
            system_message=self.context.system_prompt,
        )

        logger.info(f"  {self.context.agent_name} agent compiled successfully")
        return self

    def _ensure_compiled(self) -> None:
        """Ensure the agent has been compiled before invocation.

        Raises:
            RuntimeError: If compile() has not been called
        """
        if not self._agent:
            raise RuntimeError(
                f"{self.context.agent_name} not compiled. Call compile() first."
            )

    def _extract_tools_used(self, result: Any) -> list[str]:
        """Extract list of tools used from agent response messages.

        Parses through agent messages to find tool call content blocks
        and extracts their names.

        Args:
            result: The agent run result containing messages

        Returns:
            List of tool names that were invoked
        """
        tools_used = []
        if not hasattr(result, "messages"):
            return tools_used

        for msg in result.messages:
            if hasattr(msg, "content") and isinstance(msg.content, list):
                for content_part in msg.content:
                    if hasattr(content_part, "name"):
                        tools_used.append(content_part.name)
        return tools_used

    def _extract_content_from_response(
        self,
        result: Any,
        content_key: str = "content"
    ) -> dict[str, Any]:
        """Extract structured content from agent response.

        Attempts to parse the last message as JSON. If parsing fails,
        wraps the content in a dictionary with the specified key.

        Args:
            result: The agent run result containing messages
            content_key: Key to use when wrapping non-JSON content

        Returns:
            Dictionary with extracted content
        """
        if not hasattr(result, "messages") or not result.messages:
            return {}

        content = str(result.messages[-1].content)
        try:
            if content.startswith("{"):
                return json.loads(content)
            return {f"{content_key}_text": content}
        except json.JSONDecodeError:
            return {f"{content_key}_text": content}

    def _get_last_message_content(self, result: Any) -> str:
        """Get the content of the last message from agent response.

        Args:
            result: The agent run result containing messages

        Returns:
            String content of the last message, or empty string if not available
        """
        if hasattr(result, "messages") and result.messages:
            return str(result.messages[-1].content)
        return ""

    @abstractmethod
    async def invoke(self, task: str) -> Any:
        """Invoke the agent with a task.

        Subclasses must implement this method to define their specific
        invocation logic and output structure.

        Args:
            task: The task or query for the agent to process

        Returns:
            Agent-specific output (dict, Pydantic model, etc.)
        """
        pass
