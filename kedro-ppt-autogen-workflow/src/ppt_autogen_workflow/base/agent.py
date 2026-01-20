"""Base agent classes for AutoGen integration."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from autogen_agentchat.agents import AssistantAgent
from kedro.pipeline.llm_context import LLMContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseAgent")


class BaseAgent(ABC, Generic[T]):
    """Base class for AutoGen agents with LLMContext integration."""

    agent_name: str = "Agent"
    system_prompt_key: str = ""

    def __init__(self, llm_context: LLMContext) -> None:
        """Initialize the agent with LLMContext."""
        self._llm_context = llm_context
        self._agent: AssistantAgent | None = None

    def compile(self: T) -> T:
        """Compile and initialize the AutoGen AssistantAgent."""
        logger.info(f"Compiling {self.agent_name} agent...")

        # Extract system prompt
        system_prompt = self._llm_context.prompts.get(self.system_prompt_key)
        system_prompt_text = (
            system_prompt.format() if hasattr(system_prompt, 'format')
            else str(system_prompt) if system_prompt else ""
        )

        # Flatten tools - tool builder functions return lists of FunctionTools
        tools = []
        for tool_or_list in self._llm_context.tools.values():
            if isinstance(tool_or_list, list):
                tools.extend(tool_or_list)
            else:
                tools.append(tool_or_list)

        self._agent = AssistantAgent(
            name=self.agent_name,
            model_client=self._llm_context.llm,
            tools=tools,
            system_message=system_prompt_text,
        )

        logger.info(f"  {self.agent_name} agent compiled successfully")
        return self

    def _ensure_compiled(self) -> None:
        """Ensure the agent has been compiled before invocation."""
        if not self._agent:
            raise RuntimeError(
                f"{self.agent_name} not compiled. Call compile() first."
            )

    async def _run_with_output(
        self, task: str, output_type: type[BaseModel]
    ) -> BaseModel:
        """Run agent and return structured output as Pydantic model."""
        self._ensure_compiled()
        result = await self._agent.run(task=task)

        # Try to extract structured data from messages
        if hasattr(result, 'messages') and result.messages:
            for msg in reversed(result.messages):
                parsed = self._try_parse_message(msg, output_type)
                if parsed:
                    return parsed

        return output_type()

    def _try_parse_message(
        self, msg: Any, output_type: type[BaseModel]
    ) -> BaseModel | None:
        """Try to parse a message into the output type."""
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
        """Invoke the agent with a task."""
        pass
