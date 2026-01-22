from datetime import datetime
import logging

from kedro.pipeline import LLMContext
from kedro.pipeline.preview_contract import MermaidPreview, TextPreview

from langchain_core.messages import AIMessage
from sqlalchemy import text, Engine

from .agent import ResponseGenerationAgent
from ...utils import log_message

logger = logging.getLogger(__name__)


def make_preview_fn(data_sample):
    """Create a preview function with captured context."""
    def preview_fn() -> TextPreview:
        return TextPreview(content=data_sample, meta={"language": "python"})
    return preview_fn


def generate_code_preview() -> TextPreview:
    """Generate a code preview with syntax highlighting.

    Returns:
        TextPreview object with code content and language metadata
    """
    code = """def calculate_metrics(data):
    \"\"\"Calculate key performance metrics.\"\"\"
    import pandas as pd

    metrics = {
        'mean': data.mean(),
        'median': data.median(),
        'std': data.std()
    }

    return pd.DataFrame(metrics)

# Example usage
result = calculate_metrics(my_dataframe)
print(result)"""

    return TextPreview(content=code, meta={"language": "python"})


def generate_mermaid_preview() -> MermaidPreview:
    compiled = ResponseGenerationAgent.graph().compile()
    mermaid = compiled.get_graph().draw_mermaid()
    return MermaidPreview(content=mermaid)


def generate_response(
    response_generation_context: LLMContext,
    intent_detection_result: dict,
    user_context: dict,
    session_config: dict,
) -> dict:
    """
    Run the ResponseGenerationAgent to produce a final answer.
    Accepts intent detection result + user context and session config.
    """
    if intent_detection_result["intent"] == "clarification_needed":
        message = (
            "Failed to recognize intent. Please try to describe your problem briefly."
        )
        logger.warning(message)

        result = {"messages": [AIMessage(content=message)]}

    else:
        agent = ResponseGenerationAgent(context=response_generation_context)
        agent.compile()

        context = {
            "messages": [],
            "intent": intent_detection_result["intent"],
            "intent_generator_summary": intent_detection_result["reason"],
            "user_context": user_context,
        }

        result = agent.invoke(context, session_config)

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
