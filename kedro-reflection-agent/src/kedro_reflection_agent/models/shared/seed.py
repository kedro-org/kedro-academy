"""Global base seed models — shared across all agents."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CustomerBase(BaseModel):
    """Global customer master record (data/shared/seed/customers.json)."""

    customer_id: str
    name: str
    type: Literal["enterprise", "consumer"]
    region: str
    tenure_years: float


class ProductBase(BaseModel):
    """Global product catalogue record (data/shared/seed/products.json)."""

    product_id: str
    name: str
    type: Literal["enterprise_solution", "consumer_plan", "device"]
    tier: Literal["basic", "standard", "premium"]


class CampaignTarget(BaseModel):
    """One row of targets.json — which (customer, product) pair to run.

    Shared schema across all agents (data/{agent_id}/seed/targets.json).
    The case_id is the join key linking campaign outputs, eval cases, scores,
    and signals throughout the pipeline.
    """

    case_id: str
    customer_id: str
    product_id: str
