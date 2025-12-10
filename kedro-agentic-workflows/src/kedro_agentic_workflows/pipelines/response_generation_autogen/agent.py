import asyncio
from typing import List

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel, Field

from ...utils import KedroAgent, AgentContext


class ResponseOutput(BaseModel):
    """Structured schema for the final response."""
    message: str = Field(..., description="Final message for the user")
    claim_created: bool = Field(default=False, description="Whether a claim was created")
    escalation: bool = Field(default=False, description="Whether escalation is needed")


class ResponseGenerationAgentAutogen(KedroAgent):
    """Response generation agent using Autogen agents."""
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.tool_agent: AssistantAgent | None = None
        self.tools = self.context.tools
        self.tool_prompt = self.context.get_prompt("tool_prompt")
        self.llm = self.context.llm

        self.response_prompt = self.context.get_prompt("response_prompt")
        self.response_agent: AssistantAgent | None = None

    def compile(self):
        """Initialize the Agent with its tools and instructions."""
        self.tool_agent = AssistantAgent(
            name="response_generation_agent_tools",
            system_message="Decide which tools to use.",
            tools=list(self.tools.values()),
            model_client=self.llm,
        )

        self.response_agent = AssistantAgent(
            name="response_generation_agent_response",
            system_message="Generate final structured response using tool results.",
            model_client=self.llm,
            output_content_type=ResponseOutput
        )

    def invoke(self, context: dict, config: dict | None = None) -> dict:
        """Run the agent and produce the response in the same form as previously."""
        if self.tool_agent is None:
            raise ValueError(f"{self.__class__.__name__} must be compiled before invoking. Call .compile() first.")

        # Collect initial messages
        messages: List[BaseMessage] = []

        dynamic_context = {
            "intent": context["intent"],
            "intent_generator_summary": context.get("intent_generator_summary", ""),
            "user_id": context.get("user_context", {}).get("profile", {}).get("user_id", "unknown"),
        }

        tool_instructions = self.tool_prompt.format(**dynamic_context)
        tool_result: TaskResult = asyncio.run(self.tool_agent.run(task=tool_instructions))

        try:
            function_called = tool_result.messages[-2].content[0].name
        except Exception:
            function_called = None

        messages.append(AIMessage(content=tool_result.messages[-1].content))

        created_claim = ""
        doc_results = ""
        user_claims = ""

        if function_called == "create_claim":
            created_claim = tool_result.messages[-1].content
        elif function_called == "lookup_docs":
            doc_results = tool_result.messages[-1].content
        elif function_called == "get_user_claims":
            user_claims = tool_result.messages[-1].content

        dynamic_context = {
            "intent": context["intent"],
            "intent_generator_summary": context.get("intent_generator_summary", ""),
            "user_context": context.get("user_context", ""),
            "created_claim": created_claim,
            "docs_lookup": doc_results,
            "user_claims": user_claims,
        }

        response_instructions = self.response_prompt.format(**dynamic_context)
        final_result: TaskResult = asyncio.run(self.response_agent.run(task=response_instructions))
        response: ResponseOutput = final_result.messages[-1].content

        messages.append(AIMessage(content=response.message))

        return {
            "messages": messages,
            "claim_created": response.claim_created,
            "escalated": response.escalation,
        }
