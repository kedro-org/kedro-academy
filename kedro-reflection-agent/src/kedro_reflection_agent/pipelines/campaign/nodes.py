"""Nodes for the ``campaign`` pipeline.

Generates personalised B2B outreach emails for each campaign target
(customer × product pair) and emits a Langfuse trace per call.

The chain composition follows the kedro-agentic-workflows pattern:
    ChatPromptTemplate | LLM.with_structured_output(EmailOutput)

The skill markdown is injected via the ``{skill}`` template variable defined in
the Langfuse-stored system prompt.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from kedro.pipeline import LLMContext
from langchain_core.prompts import ChatPromptTemplate
from langfuse.langchain import CallbackHandler

from ...data_models import Customer, Email, EmailOutput, Product, RunMetadata

logger = logging.getLogger(__name__)


def prepare_agent_inputs(
    targets: list[dict],
    customers: list[dict],
    products: list[dict],
) -> list[dict]:
    """Prepare the batch of inputs the agent will run on.

    Resolves each campaign target ``{case_id, customer_id, product_id}`` into
    fully-populated Customer / Product objects by joining against the seed
    catalogues.

    Returns one dict per case: ``{case_id, customer, product}`` ready for the
    LLM chain.
    """
    customer_by_id = {c["customer_id"]: Customer(**c) for c in customers}
    product_by_id = {p["product_id"]: Product(**p) for p in products}

    agent_inputs: list[dict] = []
    for target in targets:
        case_id = target["case_id"]
        cust_id = target["customer_id"]
        prod_id = target["product_id"]

        if cust_id not in customer_by_id:
            logger.warning("Skipping case %s: customer %s not found", case_id, cust_id)
            continue
        if prod_id not in product_by_id:
            logger.warning("Skipping case %s: product %s not found", case_id, prod_id)
            continue

        agent_inputs.append(
            {
                "case_id": case_id,
                "customer": customer_by_id[cust_id],
                "product": product_by_id[prod_id],
            }
        )

    logger.info(
        "Prepared %d agent inputs from %d campaign targets",
        len(agent_inputs),
        len(targets),
    )
    return agent_inputs


def generate_emails(
    agent_context: LLMContext,
    agent_inputs: list[dict],
    skill_text: str,
    agent_tracer: CallbackHandler,
    run_id: str,
    model_name: str,
    system_prompt_version: int,
) -> tuple[dict[str, dict], dict]:
    """Generate one email per prepared agent input.

    Returns a tuple of:
      - emails: dict[case_id, Email dict] for the PartitionedDataset
      - run_metadata: dict for the JSON run-summary dataset
    """
    chain = _build_chain(agent_context)
    skill_version = _hash_skill(skill_text)
    started_at = _utc_now_iso()

    emails: dict[str, dict] = {}
    n_errors = 0

    for agent_input in agent_inputs:
        case_id: str = agent_input["case_id"]
        customer: Customer = agent_input["customer"]
        product: Product = agent_input["product"]

        invoke_payload = {
            "skill": skill_text,
            "customer": json.dumps(customer.model_dump(), indent=2),
            "product": json.dumps(product.model_dump(), indent=2),
        }
        invoke_config: dict[str, Any] = {
            "callbacks": [agent_tracer],
            # NB: OpenTelemetry baggage propagation requires string values, so
            # we stringify everything we put on the trace. The structured Email
            # output below still carries the int `prompt_version`.
            "metadata": {
                "case_id": case_id,
                "customer_id": customer.customer_id,
                "product_id": product.product_id,
                "run_id": run_id,
                "prompt_version": str(system_prompt_version),
                "skill_version": skill_version,
            },
            "run_name": f"campaign:{case_id}",
        }

        try:
            result: EmailOutput = chain.invoke(invoke_payload, config=invoke_config)
        except Exception as exc:
            n_errors += 1
            logger.exception("Failed to generate email for case %s: %s", case_id, exc)
            continue

        email = Email(
            case_id=case_id,
            customer_id=customer.customer_id,
            product_id=product.product_id,
            subject=result.subject,
            body=result.body,
            trace_id=None,
            prompt_version=system_prompt_version,
            skill_version=skill_version,
            model_name=model_name,
            run_id=run_id,
            generated_at=_utc_now_iso(),
        )
        emails[case_id] = email.model_dump()

    finished_at = _utc_now_iso()
    run_metadata = RunMetadata(
        run_id=run_id,
        n_cases=len(agent_inputs),
        n_emails=len(emails),
        n_errors=n_errors,
        model_name=model_name,
        prompt_version=system_prompt_version,
        skill_version=skill_version,
        started_at=started_at,
        finished_at=finished_at,
    ).model_dump()

    logger.info(
        "campaign %s: generated %d/%d emails (%d errors) with model=%s prompt_v=%s skill_v=%s",
        run_id,
        run_metadata["n_emails"],
        run_metadata["n_cases"],
        run_metadata["n_errors"],
        model_name,
        system_prompt_version,
        skill_version,
    )

    return emails, run_metadata


# --- helpers -----------------------------------------------------------------


def _build_chain(agent_context: LLMContext):
    """Compose ``prompt | structured_llm`` from the LLM context."""
    raw_prompt = agent_context.prompts["system_prompt"]

    # mode: langchain on LangfusePromptDataset should give us a ChatPromptTemplate
    # directly. We defensively handle ChatPromptClient as in the source-of-truth
    # project in case the conversion isn't already applied.
    if isinstance(raw_prompt, ChatPromptTemplate):
        chat_prompt = raw_prompt
    elif hasattr(raw_prompt, "get_langchain_prompt"):
        chat_prompt = ChatPromptTemplate.from_messages(raw_prompt.get_langchain_prompt())
    else:
        chat_prompt = ChatPromptTemplate.from_messages(raw_prompt)

    structured_llm = agent_context.llm.with_structured_output(EmailOutput)
    return chat_prompt | structured_llm


def _hash_skill(skill_text: str) -> str:
    return hashlib.sha256(skill_text.encode("utf-8")).hexdigest()[:12]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
