"""Nodes for the ``campaign`` pipeline.

Generates personalised B2B outreach emails for each campaign target
(customer × product pair) and emits a Langfuse trace per call.

The chain composition follows the kedro-agentic-workflows pattern:
    ChatPromptTemplate | LLM.with_structured_output(EmailOutput)

The skill markdown is injected via the ``{skill}`` template variable defined in
the Langfuse-stored system prompt.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from kedro.pipeline import LLMContext
from langfuse.langchain import CallbackHandler

from kedro_reflection_agent.models.shared import CampaignTarget, CustomerBase, Email, EmailOutput, ProductBase, RunMetadata
from kedro_reflection_agent.pipelines._common import build_structured_chain, current_prompt_version, utc_now_iso

logger = logging.getLogger(__name__)


def prepare_agent_inputs(
    targets: list[dict],
    customers: list[dict],
    products: list[dict],
    customer_profiles: list[dict],
    product_details: list[dict],
) -> list[dict]:
    """Prepare the batch of inputs the agent will run on.

    Validates global base records (CustomerBase, ProductBase), then merges each
    with its agent-specific enrichment profile before handing to the LLM chain.

    Returns one dict per case: ``{case_id, customer, product}`` ready for the
    LLM chain.
    """
    customer_base_by_id = {CustomerBase(**c).customer_id: CustomerBase(**c).model_dump()
                           for c in customers}
    product_base_by_id = {ProductBase(**p).product_id: ProductBase(**p).model_dump()
                          for p in products}
    customer_profile_by_id = {c["customer_id"]: c for c in customer_profiles}
    product_details_by_id = {p["product_id"]: p for p in product_details}

    agent_inputs: list[dict] = []
    for raw_target in targets:
        t = CampaignTarget(**raw_target)
        case_id = t.case_id
        cust_id = t.customer_id
        prod_id = t.product_id

        if cust_id not in customer_base_by_id:
            logger.warning("Skipping case %s: customer %s not found", case_id, cust_id)
            continue
        if prod_id not in product_base_by_id:
            logger.warning("Skipping case %s: product %s not found", case_id, prod_id)
            continue

        customer = {
            **customer_base_by_id[cust_id],
            **customer_profile_by_id.get(cust_id, {}),
        }
        product = {
            **product_base_by_id[prod_id],
            **product_details_by_id.get(prod_id, {}),
        }

        agent_inputs.append(
            {
                "case_id": case_id,
                "customer": customer,
                "product": product,
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
    agent_id: str,
    model_name: str,
) -> tuple[dict[str, dict], dict]:
    """Generate one email per prepared agent input.

    Returns a tuple of:
      - emails: dict[case_id, Email dict] for the PartitionedDataset
      - run_metadata: dict for the JSON run-summary dataset
    """
    chain = build_structured_chain(agent_context, "system_prompt", EmailOutput)
    prompt_version = current_prompt_version(agent_id)
    started_at = utc_now_iso()
    run_started = time.perf_counter()

    emails: dict[str, dict] = {}
    n_errors = 0
    total = len(agent_inputs)

    logger.info(
        "campaign %s: starting %d generations | model=%s prompt_v=%d",
        run_id,
        total,
        model_name,
        prompt_version,
    )

    for idx, agent_input in enumerate(agent_inputs, start=1):
        case_id: str = agent_input["case_id"]
        customer: dict = agent_input["customer"]
        product: dict = agent_input["product"]

        logger.info(
            "[%d/%d] %s: %s × %s",
            idx, total, case_id, customer["customer_id"], product["product_id"],
        )

        invoke_payload = {
            "skill": skill_text,
            "customer": json.dumps(customer, indent=2),
            "product": json.dumps(product, indent=2),
        }
        invoke_config: dict[str, Any] = {
            "callbacks": [agent_tracer],
            "metadata": {
                "case_id": case_id,
                "customer_id": customer["customer_id"],
                "product_id": product["product_id"],
                "run_id": run_id,
                "system_prompt_version": str(prompt_version),
            },
            "run_name": f"campaign:{case_id}",
        }

        case_started = time.perf_counter()
        try:
            result: EmailOutput = chain.invoke(invoke_payload, config=invoke_config)
        except Exception:
            n_errors += 1
            logger.exception("[%d/%d] %s: FAILED", idx, total, case_id)
            continue

        emails[case_id] = Email(
            case_id=case_id,
            customer_id=customer["customer_id"],
            product_id=product["product_id"],
            subject=result.subject,
            body=result.body,
            trace_id=None,
            prompt_version=prompt_version,
            model_name=model_name,
            run_id=run_id,
            generated_at=utc_now_iso(),
        ).model_dump()

        logger.info(
            "[%d/%d] %s: done in %.1fs",
            idx, total, case_id, time.perf_counter() - case_started,
        )

    finished_at = utc_now_iso()
    total_elapsed = time.perf_counter() - run_started
    run_metadata = RunMetadata(
        run_id=run_id,
        agent_id=agent_id,
        n_cases=len(agent_inputs),
        n_emails=len(emails),
        n_errors=n_errors,
        model_name=model_name,
        prompt_version=prompt_version,
        started_at=started_at,
        finished_at=finished_at,
    ).model_dump()

    avg = total_elapsed / total if total else 0.0
    logger.info(
        "campaign %s: generated %d/%d emails (%d errors) in %.1fs (avg %.1fs/case) "
        "| model=%s prompt_v=%d skill_v=%d",
        run_id,
        run_metadata["n_emails"],
        run_metadata["n_cases"],
        run_metadata["n_errors"],
        total_elapsed,
        avg,
        model_name,
        prompt_version,
        prompt_version,
    )

    return emails, run_metadata


