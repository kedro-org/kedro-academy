"""Base agent classes for AutoGen integration.

This module provides shared base classes for all AutoGen agents in the project.
Both single-agent and multi-agent pipelines can inherit from BaseAgent to
eliminate code duplication.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from pydantic import BaseModel

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
    - Structured output handling via Pydantic models

    Subclasses implement the invoke() method and use _run_with_output()
    to get typed responses.

    Example:
        ```python
        class MyAgent(BaseAgent["MyAgent"]):
            async def invoke(self, task: str) -> MyOutput:
                return await self._run_with_output(task, MyOutput)
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

    async def _run_with_output(
        self, task: str, output_type: type[BaseModel]
    ) -> BaseModel:
        """Run agent and return structured output.

        Runs the agent and parses the response into a Pydantic model.
        Looks for tool results first, then tries to parse raw content.

        Args:
            task: The task for the agent to process
            output_type: Pydantic model class for structured output

        Returns:
            Instance of output_type with agent's response
        """
        self._ensure_compiled()
        result = await self._agent.run(task=task)

        # Try to extract structured data from messages
        if hasattr(result, 'messages') and result.messages:
            for msg in reversed(result.messages):
                parsed = self._try_parse_message(msg, output_type)
                if parsed:
                    return parsed

        # Return default instance if parsing fails
        return output_type()

    def _try_parse_message(
        self, msg: Any, output_type: type[BaseModel]
    ) -> BaseModel | None:
        """Try to parse a message into the output type.

        Args:
            msg: Message from agent response
            output_type: Pydantic model class to parse into

        Returns:
            Parsed model instance or None if parsing fails
        """
        import json

        if not hasattr(msg, 'content'):
            return None

        content = msg.content

        # Handle list content (tool results)
        if isinstance(content, list):
            for item in content:
                if hasattr(item, 'content'):
                    try:
                        data = json.loads(item.content) if isinstance(item.content, str) else item.content
                        if isinstance(data, dict):
                            return output_type(**data)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        continue

        # Handle string content
        if isinstance(content, str):
            content = content.strip()
            if content.startswith('{'):
                try:
                    data = json.loads(content)
                    return output_type(**data)
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

        return None

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
