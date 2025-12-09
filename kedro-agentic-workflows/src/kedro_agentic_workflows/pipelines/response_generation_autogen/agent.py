import asyncio
import json

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
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

    def compile(self):
        """Initialize the Agent with its tools and instructions."""
        self.tool_agent = AssistantAgent(
            name="response_generation_agent_tools",
            system_message="Decide which tools to use.",
            tools=list(self.tools.values()),
            model_client=self.llm,
        )

    def invoke(self, context: dict, config: dict | None = None) -> dict:
        """Run the agent and produce the response in the same form as previously."""
        if self.tool_agent is None:
            raise ValueError(f"{self.__class__.__name__} must be compiled before invoking. Call .compile() first.")

        dynamic_context = {
            "intent": context["intent"],
            "intent_generator_summary": context.get("intent_generator_summary", ""),
            "user_id": context.get("user_context", {}).get("profile", {}).get("user_id", "unknown"),
        }

        tool_instructions = self.tool_prompt.format(**dynamic_context)

        tool_result: TaskResult = asyncio.run(self.tool_agent.run(task=tool_instructions))
        print("---")
        print(tool_result.messages)
        print("---")

        # tool_result.messages → full conversation
        # tool_result.artifacts → tool call outputs indexed by tool name
        created_claim = tool_result.artifacts.get("create_claim")
        doc_results = tool_result.artifacts.get("lookup_docs")
        user_claims = tool_result.artifacts.get("get_user_claims")

        # Normalise formatting for response prompt
        def fmt(v):
            if not v:
                return "None"
            try:
                return json.dumps(v, indent=2)
            except Exception:
                return str(v)

        dynamic_context = {
            "intent": context["intent"],
            "intent_generator_summary": context.get("intent_generator_summary", ""),
            "user_context": context.get("user_context", ""),
            "created_claim": fmt(created_claim),
            "docs_lookup": fmt(doc_results),
            "user_claims": fmt(user_claims),
        }

        return {}