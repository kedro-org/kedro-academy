from datetime import datetime
import logging
from typing import Any

from kedro.pipeline import LLMContext
from langchain_core.messages import AIMessage
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from sqlalchemy import text, Engine

from .agent import ResponseGenerationAgentAutogen
from ...utils import log_message

logger = logging.getLogger(__name__)


def setup_autogen_tracing(span_processor: Any) -> TracerProvider:
    """Set up OpenTelemetry tracing with Langfuse for AutoGen.

    This function configures OpenTelemetry to send traces to Langfuse.
    Must be called before running any AutoGen agents.

    Args:
        span_processor: LangfuseSpanProcessor from the LangfuseTraceDataset.

    Returns:
        TracerProvider: The configured tracer provider.
    """
    provider = TracerProvider()
    provider.add_span_processor(span_processor)
    trace.set_tracer_provider(provider)

    logger.info("Langfuse tracing configured for AutoGen agents")
    return provider


def generate_response(
    response_generation_context: LLMContext,
    intent_detection_result: dict,
    user_context: dict,
    session_config: dict,
    tracer_provider: TracerProvider,
) -> dict:
    """
    Run the ResponseGenerationAgent to produce a final answer.
    Accepts intent detection result + user context and session config.
    """
    # Get a tracer for creating spans
    tracer = trace.get_tracer(__name__)

    if intent_detection_result["intent"] == "clarification_needed":
        message = (
            "Failed to recognize intent. Please try to describe your problem briefly."
        )
        logger.warning(message)

        result = {"messages": [AIMessage(content=message)]}

    else:
        # Wrap agent execution in a span for tracing
        with tracer.start_as_current_span("response_generation") as span:
            # Log input context to the span
            span.set_attribute("intent", intent_detection_result["intent"])
            span.set_attribute(
                "intent_reason", intent_detection_result.get("reason", "")
            )
            span.set_attribute(
                "user_id",
                user_context.get("profile", {}).get("user_id", "unknown"),
            )

            agent = ResponseGenerationAgentAutogen(context=response_generation_context)
            agent.compile()

            context = {
                "messages": [],
                "intent": intent_detection_result["intent"],
                "intent_generator_summary": intent_detection_result["reason"],
                "user_context": user_context,
            }

            result = agent.invoke(context, session_config)

            # Log output to the span
            if result.get("messages"):
                span.set_attribute(
                    "response", result["messages"][-1].content[:500]
                )  # Truncate for safety
            span.set_attribute("claim_created", result.get("claim_created", False))
            span.set_attribute("escalated", result.get("escalated", False))

    for m in result["messages"]:
        try:
            m.pretty_print()
        except Exception:
            print(m)

    return result


def log_response_and_end_session(
    db_engine: Engine, session_id: int, final_response: dict
):
    """Log all messages and mark the session as ended."""
    for m in final_response["messages"]:
        log_message(db_engine, session_id, m)

    ended_at = datetime.utcnow()
    query = text("""
        UPDATE session
        SET ended_at = :ended_at
        WHERE id = :session_id
    """)
    with db_engine.begin() as conn:
        conn.execute(query, {"ended_at": ended_at, "session_id": session_id})

    logger.info("Session session_id %s ended at ended_at %s", session_id, ended_at)
