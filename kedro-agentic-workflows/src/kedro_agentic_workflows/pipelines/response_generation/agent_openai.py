from typing import Any, TypedDict, List
from pydantic import BaseModel, Field
from agents import Agent, Runner, Tool
from agents.items import ToolCallOutputItem, MessageOutputItem
from agents.run import RunResult
from langchain_core.messages import AIMessage, BaseMessage

from ...utils import KedroAgent, AgentContext


class AgentState(TypedDict):
    messages: List[BaseMessage]
    intent: str
    intent_generator_summary: str
    user_context: dict


class ResponseOutput(BaseModel):
    """Structured schema for the final response."""
    message: str = Field(..., description="Final message for the user")
    claim_created: bool = Field(default=False, description="Whether a claim was created")
    escalation: bool = Field(default=False, description="Whether escalation is needed")


class ResponseGenerationAgent(KedroAgent):
    """
    Response generation agent using OpenAI Agents SDK.
    Maintains the same compile()/invoke() interface as before for Kedro integration.
    """

    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.tool_agent: Agent | None = None
        self.response_agent: Agent | None = None
        self.tools = self.context.tools
        self.tool_prompt = self.context.get_prompt("tool_prompt")
        self.response_prompt = self.context.get_prompt("response_prompt")

    def compile(self):
        """Initialize the Agent with its tools and instructions."""
        # Wrap each tool function into a Tool object
        openai_tools: List[Tool] = []
        for name, fn in self.tools.items():
            openai_tools.append(
                Tool(
                    name=name,
                    description=fn.__doc__ or f"Tool: {name}",
                    func=fn,
                )
            )

        self.tool_agent = Agent(
            name="response_generation_agent_tools",
            instructions=self.tool_prompt,
            tools=openai_tools,
            model=self.context.llm,
        )

        self.response_agent = Agent(
            name="response_generation_agent_response",
            instructions=self.response_prompt,
            model=self.context.llm,
            output_type=ResponseOutput,
        )

    def invoke(self, context: dict, config: dict | None = None) -> dict:
        """
        Run the agent and produce the response in the same form as previously.
        """
        if self.tool_agent is None:
            raise ValueError(f"{self.__class__.__name__} must be compiled before invoking. Call .compile() first.")

        # Build prompt for tool‐decision phase and run the agent
        dynamic_context = {
            "intent": context["intent"],
            "intent_generator_summary": context.get("intent_generator_summary", ""),
            "user_id": context.get("user_context", {}).get("profile", {}).get("user_id", "unknown"),
        }
        run_result: RunResult = Runner.run_sync(
            self.tool_agent,
            input="Decide which tools to use.",
            context=dynamic_context,
        )

        # Collect initial messages
        messages: List[BaseMessage] = []
        for item in run_result.new_items:
            if isinstance(item, MessageOutputItem):
                messages.append(AIMessage(content=str(item.raw_item.content)))
            elif isinstance(item, ToolCallOutputItem):
                messages.append(AIMessage(content=str(item.output)))

        # Extract tool call outputs for generating structured response
        created_claims = [
            item.output for item in run_result.new_items
            if isinstance(item, ToolCallOutputItem) and getattr(item.raw_item, "tool_name", "") == "create_claim"
        ]
        doc_lookups = [
            item.output for item in run_result.new_items
            if isinstance(item, ToolCallOutputItem) and getattr(item.raw_item, "tool_name", "") == "lookup_docs"
        ]
        user_claims = [
            item.output for item in run_result.new_items
            if isinstance(item, ToolCallOutputItem) and getattr(item.raw_item, "tool_name", "") == "get_user_claims"
        ]

        created_claim_str = "\n".join(map(str, created_claims))
        doc_results_str = "\n".join(map(str, doc_lookups))
        user_claims_str = "\n".join(map(str, user_claims))

        dynamic_context = {
            "intent": context["intent"],
            "intent_generator_summary": context.get("intent_generator_summary", ""),
            "user_context": context.get("user_context", ""),
            "created_claim": created_claim_str,
            "docs_lookup": doc_results_str,
            "user_claims": user_claims_str,
        }

        final_result: RunResult = Runner.run_sync(
            self.response_agent,
            input="Generate the final structured response using tool results.",
            context=dynamic_context,
        )
        response: ResponseOutput = final_result.final_output

        # Append to messages
        messages.append(AIMessage(content=response.message))

        return {
            "messages": messages,
            "claim_created": response.claim_created,
            "escalated": response.escalation,
        }
