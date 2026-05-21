"""Campaign agent run nodes."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from kedro_reflection_agent.utils.eval_dataset_format import from_langfuse_items
from kedro_reflection_agent.base.llm import invoke_text
from kedro_reflection_agent.data_models import CustomerProfile, EmailMetadata, EmailOutput, EvalCase, ProductProfile
from kedro_reflection_agent.utils.prompt_utils import prompt_text

logger = logging.getLogger(__name__)


def _index_by_id(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {r[key]: r for r in records}


def _record_email_generation(
    client: Any,
    *,
    langfuse_host: str,
    langfuse_project_id: str,
    metadata: dict[str, Any],
    model: str,
    system: str,
    user: str,
    output: dict[str, Any],
) -> tuple[str | None, str | None]:
    if client is None:
        return None, None
    try:
        with client.start_as_current_observation(
            name="campaign_email_generation",
            as_type="span",
            metadata=metadata,
            input={"system": system, "user": user},
        ) as span:
            with span.start_as_current_observation(
                name="email_generation",
                as_type="generation",
                model=model,
                input={"system": system, "user": user},
                output=output,
            ):
                pass
            span.update(output=output)
            trace_id = span.trace_id
        client.flush()
        host = langfuse_host.rstrip("/")
        url = f"{host}/project/{langfuse_project_id}/traces/{trace_id}" if langfuse_project_id else f"{host}/trace/{trace_id}"
        return trace_id, url
    except Exception as exc:  # noqa: BLE001
        logger.warning("Langfuse trace failed: %s", exc)
        return None, None


def generate_emails(
    eval_cases_file: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
    skill_file: str,
    langfuse_tracer: Any,
    agent_llm_context: LLMContext,
    parameters: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eval_dataset = from_langfuse_items(eval_cases_file)
    run_id = parameters.get("run_id", "run_1")
    langfuse_host = parameters.get("langfuse_host", "https://cloud.langfuse.com")
    langfuse_project_id = parameters.get("langfuse_project_id", "")

    system_prompt = prompt_text(agent_llm_context.prompts.get("campaign_system_prompt", ""))
    skill_version = hashlib.sha256(skill_file.encode()).hexdigest()[:12]
    prompt_version = (
        "v2" if "personalised" in system_prompt.lower() or "personalized" in system_prompt.lower() else "v1"
    )

    cust_map = _index_by_id(customers, "customer_id")
    prod_map = _index_by_id(products, "product_id")
    lf = langfuse_tracer if parameters.get("demo_use_langfuse", True) else None

    emails: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []

    for raw_case in eval_dataset:
        case = EvalCase.model_validate(raw_case)
        customer = CustomerProfile.model_validate(cust_map[case.customer_id])
        product = ProductProfile.model_validate(prod_map[case.product_id])

        user_payload = {
            "customer": customer.model_dump(),
            "product": product.model_dump(),
            "skill_markdown": skill_file,
            "ground_truth": case.ground_truth.model_dump(),
        }
        user_msg = json.dumps(user_payload, indent=2)

        raw = invoke_text(
            agent_llm_context,
            user_msg,
            extra_system="Return JSON with keys: subject, body.",
        )
        try:
            parsed = json.loads(raw) if raw.strip().startswith("{") else json.loads(
                raw[raw.find("{") : raw.rfind("}") + 1]
            )
        except json.JSONDecodeError:
            parsed = {"subject": "Follow up", "body": raw}

        trace_id, trace_link = _record_email_generation(
            lf,
            langfuse_host=langfuse_host,
            langfuse_project_id=langfuse_project_id,
            metadata={
                "demo": "kedro-reflection-agent",
                "run_id": run_id,
                "case_id": case.case_id,
                "customer_id": customer.customer_id,
                "product_id": product.product_id,
                "prompt_version": prompt_version,
                "skill_hash": skill_version,
            },
            model=parameters.get("openai_model", "gpt-4o-mini"),
            system=system_prompt,
            user=user_msg,
            output=parsed,
        )

        email = EmailOutput(
            case_id=case.case_id,
            subject=parsed.get("subject", ""),
            body=parsed.get("body", ""),
            metadata=EmailMetadata(
                prompt_version=prompt_version,
                skill_version=skill_version,
                model=parameters.get("openai_model", "gpt-4o-mini"),
                run_id=run_id,
                trace_id=trace_id,
                trace_url=trace_link,
            ),
        )
        emails.append(email.model_dump())
        traces.append(
            {
                "case_id": case.case_id,
                "trace_id": trace_id,
                "trace_url": trace_link,
                "company_name": customer.company_name,
                "product_name": product.name,
            }
        )

    return emails, traces
