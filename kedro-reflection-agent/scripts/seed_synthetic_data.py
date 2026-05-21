#!/usr/bin/env python3
"""Seed synthetic customers, products, eval cases, prompts, and demo state (no Kedro pipeline)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kedro_reflection_agent.utils.eval_dataset_format import to_langfuse_items  # noqa: E402
from kedro_reflection_agent.utils.prompt_utils import SEED_PROMPT, SEED_SKILL  # noqa: E402

DEFAULT_EVAL_CASE_COUNT = 5


def generate_customers() -> list[dict[str, Any]]:
    specs = [
        ("cust_001", "Northstar Logistics", "Logistics", 850, 18, "UK & Ireland", ["MPLS", "Business Broadband"], ["rising network costs", "warehouse connectivity gaps"], ["fleet digitisation", "IoT tracking"]),
        ("cust_002", "Harborview Health", "Healthcare", 1200, 9, "US East", ["MPLS", "DIA"], ["clinical app latency", "remote clinic connectivity"], ["telehealth expansion", "EHR cloud migration"]),
        ("cust_003", "ForgeWorks Manufacturing", "Manufacturing", 2200, 6, "DACH", ["SD-WAN pilot", "4G backup"], ["OT/IT convergence", "predictive maintenance"], ["factory automation", "private 5G trials"]),
        ("cust_004", "BrightCart Retail", "Retail", 5000, 120, "UK", ["Business Broadband"], ["POS downtime", "in-store Wi-Fi gaps"], ["unified commerce", "edge analytics"]),
        ("cust_005", "Summit Financial Group", "Financial services", 900, 4, "US", ["MPLS", "DDoS scrubbing"], ["latency-sensitive trading links", "regulatory audit trails"], ["cloud core banking", "zero-trust access"]),
        ("cust_006", "Greenfield Academy Trust", "Education", 300, 22, "UK", ["Fibre", "Wi-Fi managed"], ["campus coverage holes", "safeguarding for online learning"], ["hybrid learning", "student device programs"]),
        ("cust_007", "CityWorks Council", "Public sector", 8000, 35, "UK", ["MPLS", "Internet"], ["legacy WAN costs", "citizen digital services"], ["smart city pilots", "secure remote staff"]),
        ("cust_008", "Helios Energy Services", "Energy", 1500, 14, "Nordics", ["MPLS", "IoT SIMs"], ["field site connectivity", "SCADA reliability"], ["renewable site monitoring", "grid modernization"]),
        ("cust_009", "Clarity Legal Partners", "Professional services", 400, 3, "UK", ["Business Broadband", "SIP"], ["client confidentiality", "hybrid meeting quality"], ["secure collaboration", "document automation"]),
        ("cust_010", "Stonebridge Construction", "Construction", 1100, 25, "UK & Ireland", ["4G routers", "Business Broadband"], ["site office churn", "temporary site connectivity"], ["BIM collaboration", "site safety IoT"]),
    ]
    customers = []
    for cid, name, industry, employees, locations, region, products, pains, initiatives in specs:
        customers.append(
            {
                "customer_id": cid,
                "company_name": name,
                "industry": industry,
                "size": "Enterprise" if employees > 3000 else "Mid-market",
                "employee_count": employees,
                "locations": locations,
                "region": region,
                "current_products": products,
                "account_tenure_years": 3 + (int(cid.split("_")[1]) % 8),
                "known_pain_points": pains,
                "strategic_initiatives": initiatives,
                "tone_preference": "practical and ROI-oriented",
                "relationship_context": "long-standing account with annual renewal in Q3",
            }
        )
    return customers


def generate_products() -> list[dict[str, Any]]:
    return [
        {
            "product_id": "prod_001",
            "name": "Managed SD-WAN",
            "category": "Connectivity",
            "ideal_for": ["multi-site businesses", "cost optimization", "cloud migration"],
            "value_props": [
                "improves application performance across sites",
                "reduces dependency on legacy MPLS",
                "centralized policy and traffic management",
            ],
            "avoid_claims": ["guaranteed 50% cost reduction", "instant deployment"],
            "cta": "book a 30-minute network optimisation review",
        },
        {
            "product_id": "prod_002",
            "name": "Private 5G",
            "category": "Connectivity",
            "ideal_for": ["manufacturing campuses", "warehouse automation", "low-latency OT"],
            "value_props": [
                "dedicated spectrum for critical workloads",
                "supports mobile robotics and AGVs",
                "integrates with existing LAN/WAN",
            ],
            "avoid_claims": ["guaranteed 50% cost reduction", "instant deployment"],
            "cta": "schedule a private 5G feasibility workshop",
        },
        {
            "product_id": "prod_003",
            "name": "IoT Connectivity Management",
            "category": "IoT",
            "ideal_for": ["fleet tracking", "smart metering", "field asset monitoring"],
            "value_props": [
                "single pane for SIM lifecycle",
                "usage alerts and cost controls",
                "global coverage with local breakout",
            ],
            "avoid_claims": ["unlimited data at zero cost", "instant deployment"],
            "cta": "book an IoT connectivity assessment",
        },
        {
            "product_id": "prod_004",
            "name": "Cloud Contact Centre",
            "category": "Collaboration",
            "ideal_for": ["retail support", "public sector hotlines", "hybrid agents"],
            "value_props": [
                "omnichannel routing with CRM hooks",
                "elastic agent scaling",
                "quality analytics and coaching",
            ],
            "avoid_claims": ["100% CSAT guarantee", "instant deployment"],
            "cta": "schedule a contact centre modernisation call",
        },
        {
            "product_id": "prod_005",
            "name": "Cyber Threat Monitoring",
            "category": "Security",
            "ideal_for": ["regulated industries", "multi-site SOC coverage", "MPLS estates"],
            "value_props": [
                "24x7 correlated threat detection",
                "playbooks aligned to NIST",
                "integration with existing SIEM",
            ],
            "avoid_claims": ["zero breaches guaranteed", "instant deployment"],
            "cta": "book a security posture review",
        },
    ]


def generate_eval_cases(limit: int | None = DEFAULT_EVAL_CASE_COUNT) -> list[dict[str, Any]]:
    pairs = [
        ("case_001", "cust_001", "prod_001", ["multi-site", "network costs", "fleet digitisation"], "network optimisation review", "connect SD-WAN to warehouse and fleet connectivity needs"),
        ("case_002", "cust_002", "prod_004", ["telehealth", "clinical app latency", "EHR"], "contact centre modernisation call", "position cloud contact centre for telehealth expansion"),
        ("case_003", "cust_003", "prod_002", ["OT/IT", "predictive maintenance", "factory automation"], "private 5G feasibility workshop", "tie private 5G to OT convergence on the factory floor"),
        ("case_004", "cust_004", "prod_001", ["POS downtime", "in-store Wi-Fi", "unified commerce"], "network optimisation review", "retail SD-WAN for store and DC resilience"),
        ("case_005", "cust_005", "prod_005", ["latency-sensitive", "audit trails", "zero-trust"], "security posture review", "threat monitoring for trading and compliance"),
        ("case_006", "cust_006", "prod_004", ["campus coverage", "hybrid learning", "safeguarding"], "contact centre modernisation call", "support admissions and parent hotlines"),
        ("case_007", "cust_007", "prod_001", ["legacy WAN costs", "citizen digital services", "smart city"], "network optimisation review", "public sector WAN modernization"),
        ("case_008", "cust_008", "prod_003", ["field site connectivity", "SCADA", "renewable monitoring"], "IoT connectivity assessment", "IoT management for renewable sites"),
        ("case_009", "cust_009", "prod_005", ["client confidentiality", "hybrid meetings", "secure collaboration"], "security posture review", "legal firm threat monitoring and access control"),
        ("case_010", "cust_010", "prod_003", ["temporary site connectivity", "site safety IoT", "BIM"], "IoT connectivity assessment", "construction site IoT and temporary links"),
        ("case_011", "cust_001", "prod_003", ["fleet digitisation", "IoT tracking", "warehouse connectivity"], "IoT connectivity assessment", "fleet IoT overlay for logistics"),
        ("case_012", "cust_002", "prod_005", ["clinical app latency", "telehealth", "EHR cloud"], "security posture review", "healthcare security for cloud EHR"),
        ("case_013", "cust_003", "prod_001", ["MPLS", "cloud migration", "multi-site"], "network optimisation review", "manufacturing SD-WAN for six plants"),
        ("case_014", "cust_004", "prod_004", ["unified commerce", "POS downtime", "edge analytics"], "contact centre modernisation call", "retail customer care scaling"),
        ("case_015", "cust_005", "prod_001", ["cloud core banking", "latency-sensitive", "MPLS"], "network optimisation review", "financial SD-WAN for core banking shift"),
        ("case_016", "cust_006", "prod_001", ["campus coverage", "hybrid learning", "student devices"], "network optimisation review", "education SD-WAN across 22 campuses"),
        ("case_017", "cust_007", "prod_005", ["citizen digital services", "secure remote staff", "legacy WAN"], "security posture review", "public sector SOC coverage"),
        ("case_018", "cust_008", "prod_002", ["grid modernization", "field sites", "SCADA reliability"], "private 5G feasibility workshop", "energy private 5G for field assets"),
        ("case_019", "cust_009", "prod_004", ["document automation", "hybrid meetings", "confidentiality"], "contact centre modernisation call", "legal client intake and scheduling"),
        ("case_020", "cust_010", "prod_002", ["site safety IoT", "temporary connectivity", "factory automation"], "private 5G feasibility workshop", "construction site private 5G for safety IoT"),
    ]
    if limit is not None:
        pairs = pairs[:limit]
    cases = []
    for case_id, cust, prod, must_mention, cta_type, angle in pairs:
        cases.append(
            {
                "case_id": case_id,
                "customer_id": cust,
                "product_id": prod,
                "ground_truth": {
                    "must_mention": must_mention,
                    "must_not_mention": ["guaranteed 50% cost reduction", "instant deployment"],
                    "desired_cta_type": cta_type,
                    "personalization_angle": angle,
                    "target_persona": "IT Director",
                },
            }
        )
    return cases


def _eval_case_limit() -> int:
    import yaml

    params_path = ROOT / "conf/base/parameters.yml"
    if params_path.exists():
        params = yaml.safe_load(params_path.read_text(encoding="utf-8")) or {}
        return int(params.get("synthetic_eval_case_count", DEFAULT_EVAL_CASE_COUNT))
    return DEFAULT_EVAL_CASE_COUNT


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_yaml_prompt(path: Path, payload: dict[str, str]) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    customers = generate_customers()
    products = generate_products()
    cases = generate_eval_cases(limit=_eval_case_limit())
    eval_langfuse = to_langfuse_items(cases)

    _write_json(ROOT / "data/seed/customers.json", customers)
    _write_json(ROOT / "data/seed/products.json", products)
    _write_json(ROOT / "data/seed/eval_cases.json", eval_langfuse)
    _write_yaml_prompt(ROOT / "data/agent_run/prompts/campaign_agent_system_prompt.yaml", SEED_PROMPT)
    _write_text(ROOT / "data/agent_run/skills/b2b-email-style.md", SEED_SKILL)
    _write_json(ROOT / "data/demo_state.json", {"state": "idle", "run_1_id": None, "proposal_id": None, "applied_id": None, "run_2_id": None})

    print(f"Seeded {len(customers)} customers, {len(products)} products, {len(cases)} eval cases.")


if __name__ == "__main__":
    main()
