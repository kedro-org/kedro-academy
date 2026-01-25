"""Base agent classes for CrewAI integration."""

from __future__ import annotations

import json
import logging
from abc import ABC
from typing import Any, Generic, TypeVar

from crewai import Agent
from kedro.pipeline.llm_context import LLMContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseAgent")


class BaseAgent(ABC, Generic[T]):
    """Base class for CrewAI agents with LLMContext integration."""

    agent_name: str = "Agent"
    system_prompt_key: str = ""

    def __init__(self, llm_context: LLMContext) -> None:
        """Initialize the agent with LLMContext.

        Args:
            llm_context: LLMContext containing LLM, prompts, and tools
        """
        self._llm_context = llm_context
        self._agent: Agent | None = None

    def _extract_role_goal_backstory(
        self, system_prompt: Any
    ) -> tuple[str, str, str]:
        """Extract role, goal, and backstory from system prompt.

        The system prompt dataset may contain structured YAML with role, goal, backstory fields,
        or it may be a simple text prompt. This method extracts what it can and provides defaults.

        Args:
            system_prompt: System prompt from LLMContext (may be ChatPromptTemplate or dict)

        Returns:
            Tuple of (role, goal, backstory)
        """
        # Default values derived from agent name
        role = self.agent_name.replace("Agent", "").replace("_", " ").strip()
        goal = ""
        backstory = ""

        # Try to extract from structured prompt (if it's a dict/YAML structure)
        prompt_data = None
        if isinstance(system_prompt, dict):
            prompt_data = system_prompt
        elif hasattr(system_prompt, "dataset") and hasattr(system_prompt.dataset, "load"):
            # Try to load the underlying dataset if it's a LangChainPromptDataset
            try:
                prompt_data = system_prompt.dataset.load()
            except Exception:
                pass

        # If we have structured data, extract role, goal, backstory
        if isinstance(prompt_data, dict):
            role = prompt_data.get("role", role)
            goal = prompt_data.get("goal", goal)
            backstory = prompt_data.get("backstory", backstory)
            # If backstory is still empty, try "description" or "system_message"
            if not backstory:
                backstory = prompt_data.get("description", prompt_data.get("system_message", ""))

        # Get the formatted prompt text for backstory if not already set
        if not backstory:
            try:
                if hasattr(system_prompt, "format"):
                    formatted = system_prompt.format()
                    if isinstance(formatted, list) and formatted:
                        content = str(formatted[0].content if hasattr(formatted[0], "content") else formatted[0])
                    else:
                        content = str(formatted)
                else:
                    content = str(system_prompt) if system_prompt else ""
                backstory = content.strip()
            except Exception:
                backstory = str(system_prompt) if system_prompt else ""

        # Fallback: derive from agent name if role is empty
        if not role:
            role = self.agent_name

        # Fallback: generic goal if not extracted
        if not goal:
            goal = f"Execute tasks as {role}"

        # Fallback: use agent name as backstory if still empty
        if not backstory:
            backstory = f"You are a {role}."

        return role, goal, backstory

    def compile(self: T) -> T:
        """Compile and initialize the CrewAI Agent.

        Returns:
            Self for method chaining
        """
        logger.info(f"Compiling {self.agent_name} agent...")

        # Extract system prompt
        system_prompt = self._llm_context.prompts.get(self.system_prompt_key)
        
        # Extract role, goal, and backstory from system prompt
        role, goal, backstory = self._extract_role_goal_backstory(system_prompt)

        # Extract tools from context
        tools = []
        for tool in self._llm_context.tools.values():
            if isinstance(tool, list):
                tools.extend(tool)
            else:
                tools.append(tool)

        # Create CrewAI Agent
        # CrewAI uses role, goal, backstory to structure the agent
        # The system prompt content is used as backstory
        # Note: llm may be a factory (callable) due to pickle constraints, so call it if needed
        llm = self._llm_context.llm
        if callable(llm) and not hasattr(llm, "call"):
            llm = llm()

        self._agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=llm,
            tools=tools,
            verbose=True,
            allow_delegation=False,
        )

        logger.info(f"  {self.agent_name} agent compiled successfully")
        return self

    def _ensure_compiled(self) -> None:
        """Ensure the agent has been compiled before invocation."""
        if not self._agent:
            raise RuntimeError(
                f"{self.agent_name} not compiled. Call compile() first."
            )

    @property
    def agent(self) -> Agent:
        """Get the compiled CrewAI agent.

        Returns:
            Compiled Agent instance

        Raises:
            RuntimeError: If agent not compiled
        """
        self._ensure_compiled()
        return self._agent

    def _try_parse_output(
        self, output: Any, output_type: type[BaseModel]
    ) -> BaseModel | None:
        """Try to parse output into the output type.

        Args:
            output: Output from agent/task execution
            output_type: Pydantic model type to parse into

        Returns:
            Parsed model instance or None if parsing fails
        """
        if output is None:
            return None

        # Handle string output
        if isinstance(output, str):
            output = output.strip()
            if output.startswith("{"):
                try:
                    data = json.loads(output)
                    if isinstance(data, dict):
                        return output_type(**data)
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

        # Handle dict output
        if isinstance(output, dict):
            try:
                return output_type(**output)
            except (TypeError, ValueError):
                pass

        # Handle object with content attribute
        if hasattr(output, "content"):
            return self._try_parse_output(output.content, output_type)

        return None

    def invoke(self, task: str) -> Any:
        """Convenience method for single-agent execution.

        Note: This method is not used in multi-agent CrewAI workflows.
        In CrewAI, agents are invoked through Tasks within a Crew, not directly.
        This method is provided for potential single-agent use cases or testing.

        Args:
            task: Task description or input

        Returns:
            Agent output (implementation would use CrewAI agent execution)

        Raises:
            NotImplementedError: Direct agent invocation not implemented for CrewAI workflows
        """
        raise NotImplementedError(
            f"{self.agent_name} agents are used within CrewAI tasks, not invoked directly. "
            "Use CrewAI Tasks and Crew for agent execution."
        )
