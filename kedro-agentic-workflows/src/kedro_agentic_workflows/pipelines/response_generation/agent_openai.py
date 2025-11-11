import json
from typing import Any, TypedDict, List

from pydantic import BaseModel, Field
from agents import Agent, Runner, Tool
from agents.items import ToolCallOutputItem, MessageOutputItem, ToolCallItem
from agents.run import RunResult
from langchain_core.messages import AIMessage, BaseMessage, messages_to_dict
from langchain_core.tools import BaseTool

from ...utils import KedroAgent, AgentContext


def langchain_to_agent_input(messages: list[BaseMessage]) -> list[dict]:
    """Convert LangChain ChatPromptTemplate messages to valid OpenAI Agent input."""
    converted = []
    for msg in messages:
        role = msg.type if msg.type in ("user", "assistant") else "user"
        content = msg.content if hasattr(msg, "content") else str(msg)
        converted.append({
            "type": "message",
            "role": role,
            "content": content,
        })
    return converted


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


class ResponseGenerationAgentOpenAI(KedroAgent):
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
        self.tool_agent = Agent(
            name="response_generation_agent_tools",
            instructions="Decide which tools to use.",
            tools=list(self.tools.values()),
            model="gpt-4o",
        )

        self.response_agent = Agent(
            name="response_generation_agent_response",
            instructions="Generate the final structured response using tool results.",
            model="gpt-4o",
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
        tool_instructions = self.tool_prompt.format(**dynamic_context)
        print("--->")
        print(tool_instructions)
        print("<---")
        run_result: RunResult = Runner.run_sync(
            self.tool_agent,
            input=tool_instructions,
        )

        for item in run_result.new_items:
            try:
                item.pretty_print()
            except Exception:
                print(item)

        # Collect initial messages
        messages: List[BaseMessage] = []
        for item in run_result.new_items:
            if isinstance(item, MessageOutputItem):
                messages.append(AIMessage(content=str(item.raw_item.content)))
            elif isinstance(item, ToolCallOutputItem):
                messages.append(AIMessage(content=str(item.output)))

        # # Extract tool call outputs for generating structured response
        # created_claims = [
        #     item.output for item in run_result.new_items
        #     if isinstance(item, ToolCallOutputItem) and getattr(item.raw_item, "tool_name", "") == "create_claim"
        # ]
        # doc_lookups = [
        #     item.output for item in run_result.new_items
        #     if isinstance(item, ToolCallOutputItem) and getattr(item.raw_item, "tool_name", "") == "lookup_docs"
        # ]
        # user_claims = [
        #     item.output for item in run_result.new_items
        #     if isinstance(item, ToolCallOutputItem) and getattr(item.raw_item, "tool_name", "") == "get_user_claims"
        # ]
        #
        # created_claim_str = "\n".join(map(str, created_claims))
        # doc_results_str = "\n".join(map(str, doc_lookups))
        # user_claims_str = "\n".join(map(str, user_claims))
        #
        # print("<---")
        # print(created_claim_str)
        # print("***")
        # print(doc_results_str)
        # print("***")
        # print(user_claims_str)
        # print("--->")

        def extract_tool_outputs(run_result):
            """Pair ToolCallItem and ToolCallOutputItem by call_id to recover tool names."""
            tool_call_map = {}
            tool_outputs = {}

            # First pass: record tool call names by call_id
            for item in run_result.new_items:
                if isinstance(item, ToolCallItem):
                    call_id = item.raw_item.call_id
                    tool_name = item.raw_item.name
                    tool_call_map[call_id] = tool_name

            # Second pass: attach outputs to those tool names
            for item in run_result.new_items:
                if isinstance(item, ToolCallOutputItem):
                    call_id = item.raw_item["call_id"]
                    tool_name = tool_call_map.get(call_id, "unknown_tool")
                    output = item.output

                    tool_outputs.setdefault(tool_name, []).append(output)

            def fmt(value):
                if not value:
                    return "None"
                try:
                    return json.dumps(value, indent=2)
                except TypeError:
                    return str(value)

            created_claim_str = fmt(tool_outputs.get("create_claim"))
            doc_results_str = fmt(tool_outputs.get("lookup_docs"))
            user_claims_str = fmt(tool_outputs.get("get_user_claims"))

            print("<---")
            print("created_claim_str:", created_claim_str)
            print("***")
            print("doc_results_str:", doc_results_str)
            print("***")
            print("user_claims_str:", user_claims_str)
            print("--->")

            return created_claim_str, doc_results_str, user_claims_str

        created_claim_str, doc_results_str, user_claims_str = extract_tool_outputs(run_result)

        dynamic_context = {
            "intent": context["intent"],
            "intent_generator_summary": context.get("intent_generator_summary", ""),
            "user_context": context.get("user_context", ""),
            "created_claim": created_claim_str,
            "docs_lookup": doc_results_str,
            "user_claims": user_claims_str,
        }

        response_instructions = self.response_prompt.format_messages(**dynamic_context)
        response_instructions = langchain_to_agent_input(response_instructions)
        print("<---")
        print(response_instructions)
        print("--->")
        final_result: RunResult = Runner.run_sync(
            self.response_agent,
            input=response_instructions,
        )
        for item in final_result.new_items:
            try:
                item.pretty_print()
            except Exception:
                print(item)
        response: ResponseOutput = final_result.final_output

        # Append to messages
        messages.append(AIMessage(content=response.message))

        return {
            "messages": messages,
            "claim_created": response.claim_created,
            "escalated": response.escalation,
        }
