"""Consumer Marketing seed models (data/consumer_mktg/seed/)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CustomerProfile(BaseModel):
    """Subscriber enrichment — FK: customer_id."""

    customer_id: str
    current_plan_id: str
    device_model: str
    data_usage_gb_monthly: float
    monthly_spend: float
    segment: Literal["budget", "mid", "premium"]


class ProductDetails(BaseModel):
    """Plan / device offer enrichment — FK: product_id."""

    product_id: str
    monthly_price: float
    key_features: list[str]
    upgrade_benefit: str
    target_segment: Literal["budget", "mid", "premium"]
