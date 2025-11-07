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
        self.agent: Agent | None = None
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

        # Create agent instance
        self.agent = Agent(
            name="response_generation_agent",
            instructions=(
                "You are a customer support assistant for claims handling. "
                "Based on intent and user context you may call tools (lookup_docs, get_user_claims, create_claim) "
                "or generate a final structured response."
            ),
            tools=openai_tools,
            model=self.context.llm,
        )

    def invoke(self, context: dict, config: dict | None = None) -> dict:
        """
        Run the agent and produce the response in the same form as previously.
        """
        if self.agent is None:
            raise ValueError(f"{self.__class__.__name__} must be compiled before invoking. Call .compile() first.")

        # Build prompt for tool‐decision phase and run the agent
        dynamic_context = {
            "intent": context["intent"],
            "intent_generator_summary": context.get("intent_generator_summary", ""),
            "user_id": context.get("user_context", {}).get("profile", {}).get("user_id", "unknown"),
        }
        run_result: RunResult = Runner.run_sync(
            self.agent,
            input=self.tool_prompt,
            context=dynamic_context,
        )

        # Collect initial messages
        messages: List[BaseMessage] = []
        for item in run_result.new_items:
            if isinstance(item, MessageOutputItem):
                messages.append(AIMessage(content=str(item.raw_item.content)))
            elif isinstance(item, ToolCallOutputItem):
                # Tool call output – include as message content for downstream logic
                # We treat tool outputs as BaseMessage via AIMessage for simplicity
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
        doc_lookups = "\n".join(map(str, user_claims))

        dynamic_context = {
            "intent": context["intent"],
            "intent_generator_summary": context.get("intent_generator_summary", ""),
            "user_context": context.get("user_context", ""),
            "created_claim": created_claim_str,
            "docs_lookup": doc_results_str,
            "user_claims": doc_lookups,
        }

        # Use the agent one more time (or reuse) to get structured output
        # Here we assume your model can output JSON that matches ResponseOutput
        final_result: RunResult = Runner.run_sync(
            self.agent,
            input=self.response_prompt,
            context=dynamic_context,
        )

        # Parse final message and structured flags
        final_message = None
        claim_created_flag = False
        escalated_flag = False

        for item in final_result.new_items:
            if isinstance(item, MessageOutputItem):
                final_message = item.raw_item.content
            # (Optionally parse tool output if your agent outputs structured JSON as tool call output)

        if final_message is None:
            raise RuntimeError("Agent did not return a final message for response.")

        # For simplicity, assume flags are encoded in JSON string within message, or you parse separately
        # You may extend this to parse JSON from final_message and extract flags
        # Here: naive placeholder
        if '"claim_created": true' in final_message.lower():
            claim_created_flag = True
        if '"escalation": true' in final_message.lower() or '"escalated": true' in final_message.lower():
            escalated_flag = True

        # Append to messages
        messages.append(AIMessage(content=final_message))

        return {
            "messages": messages,
            "claim_created": claim_created_flag,
            "escalated": escalated_flag,
        }
