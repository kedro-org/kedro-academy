"""
Tax Expert Chatbot with NIM - Optimized for speed
Single LLM call per request with keyword-based guardrails
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_nvidia_ai_endpoints.llm import NVIDIA
import mlrun
import os
import json
import re

# Blocked keywords for guardrails (no LLM call needed)
BLOCKED_PATTERNS = [
    r'\b(evade|evasion|hide\s+income|hide\s+money|offshore\s+illegal|launder)\b',
    r'\b(fraud|scam|cheat\s+irs|avoid\s+paying)\b',
]

OFF_TOPIC_KEYWORDS = ['recipe', 'weather', 'sports', 'movie', 'game', 'dating', 'music']


def init_context(context):
    """Initialize components"""
    nim_url = os.getenv("NIM_URL",
                        "nuclio-mlrun-nvidia-nim-demo-kate-my-nim-kate.default-tenant.svc.cluster.local:8080")
    model_name = os.getenv("MODEL_NAME", "meta/llama3-8b-instruct")

    protocol = "http" if ".svc.cluster.local" in nim_url or "localhost" in nim_url else "https"
    base_url = f"{protocol}://{nim_url}"

    context.logger.info(f"Connecting to: {base_url}")

    context.llm = NVIDIA(
        base_url=base_url,
        model=model_name,
        temperature=0.7,
        max_tokens=1024,
    )

    context.memory_store = {}
    context.tax_expert = create_tax_expert(context.llm)
    context.logger.info("Tax Expert ready")


def create_tax_expert(llm):
    """Tax expert - single LLM chain"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a tax education assistant. Help with:
- Income tax, brackets, deductions, credits
- 401k, IRA, Roth IRA, HSA, 529 plans  
- Capital gains, tax-loss harvesting
- Business taxes, self-employment

Previous chat: {chat_history}

Rules: Educational only. Recommend consulting a CPA for specific advice. Be concise."""),
        ("human", "{question}")
    ])
    return prompt | llm | StrOutputParser()


def check_guardrails(query: str) -> dict:
    """Fast keyword-based guardrails - no LLM call"""
    query_lower = query.lower()

    # Check blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, query_lower):
            return {"blocked": True, "reason": "Cannot assist with tax evasion or fraud."}

    # Check off-topic
    if any(kw in query_lower for kw in OFF_TOPIC_KEYWORDS):
        return {"off_topic": True}

    return {"ok": True}


def get_memory(context, session_id: str) -> str:
    """Get last 3 messages"""
    msgs = context.memory_store.get(session_id, [])[-3:]
    if not msgs:
        return "None"
    return "\n".join(f"{'Human' if m['role'] == 'human' else 'AI'}: {m['content'][:100]}" for m in msgs)


def save_memory(context, session_id: str, human_msg: str, ai_msg: str):
    """Save to memory, keep last 10"""
    if session_id not in context.memory_store:
        context.memory_store[session_id] = []
    context.memory_store[session_id].extend([
        {"role": "human", "content": human_msg},
        {"role": "assistant", "content": ai_msg}
    ])
    context.memory_store[session_id] = context.memory_store[session_id][-10:]


def handler(context, event):
    """Main handler - single LLM call"""
    try:
        # Parse request
        if not event.body:
            return context.Response(body=json.dumps({"error": "No query"}), status_code=400,
                                    content_type="application/json")

        # Convert body to string first
        if isinstance(event.body, bytes):
            body_str = event.body.decode('utf-8')
        elif isinstance(event.body, str):
            body_str = event.body
        elif isinstance(event.body, dict):
            # Already a dict
            query = event.body.get("query", "")
            session_id = event.body.get("session_id", "default")
            body_str = None
        else:
            body_str = str(event.body)

        # Parse JSON if we have a string
        if body_str is not None:
            try:
                body = json.loads(body_str)
                query = body.get("query", "")
                session_id = body.get("session_id", "default")
            except json.JSONDecodeError:
                # Treat raw string as the query
                query = body_str
                session_id = "default"

        if not query:
            return context.Response(body=json.dumps({"error": "Empty query"}), status_code=400,
                                    content_type="application/json")

        # Fast guardrail check (no LLM)
        guard = check_guardrails(query)

        if guard.get("blocked"):
            return context.Response(
                body=json.dumps({"answer": guard["reason"], "blocked": True}),
                status_code=200, content_type="application/json"
            )

        if guard.get("off_topic"):
            return context.Response(
                body=json.dumps({
                    "answer": "I only help with tax questions. Ask me about taxes, deductions, or tax-advantaged accounts!",
                    "off_topic": True}),
                status_code=200, content_type="application/json"
            )

        # Single LLM call
        response = context.tax_expert.invoke({
            "question": query,
            "chat_history": get_memory(context, session_id)
        })

        save_memory(context, session_id, query, response)

        return context.Response(
            body=json.dumps({
                "answer": response,
                "disclaimer": "Educational info only. Consult a CPA for specific advice."
            }),
            status_code=200, content_type="application/json"
        )

    except Exception as e:
        context.logger.error(f"Error: {e}")
        return context.Response(
            body=json.dumps({"error": str(e)}),
            status_code=500, content_type="application/json"
        )
