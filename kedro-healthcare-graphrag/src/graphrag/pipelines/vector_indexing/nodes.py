"""Vector indexing pipeline nodes."""
import logging

import networkx as nx

from graphrag.utils import get_openai_api_key

logger = logging.getLogger(__name__)


def create_rag_documents(entity_summaries: dict, knowledge_graph: nx.Graph) -> list:
    total = entity_summaries.get("_total_patients", 55500)
    docs = []

    for cond, stats in entity_summaries.get("conditions", {}).items():
        top_meds = sorted(stats["medication_dist"].items(), key=lambda x: -x[1])[:3]
        top_ins = sorted(stats["insurer_dist"].items(), key=lambda x: -x[1])[:3]
        pct = stats["patient_count"] / total * 100
        text = (
            f"Medical Condition: {cond}\n\n"
            f"Affects {stats['patient_count']:,} patients ({pct:.1f}% of all patients). "
            f"Average patient age: {stats['avg_age']} years. "
            f"Average billing: ${stats['avg_billing']:,.2f}. "
            f"Average hospital stay: {stats['avg_stay']} days.\n\n"
            f"Top medications: {', '.join(f'{m} ({c:,} patients)' for m, c in top_meds)}.\n"
            f"Insurance coverage: {', '.join(f'{i} ({c:,} patients)' for i, c in top_ins)}.\n"
            f"Admission breakdown: {', '.join(f'{k}: {v:,}' for k, v in stats['admission_dist'].items())}.\n"
            f"Test results: {', '.join(f'{k}: {v:,}' for k, v in stats['result_dist'].items())}.\n"
            f"Gender split: {', '.join(f'{k}: {v:,}' for k, v in stats['gender_dist'].items())}."
        )
        docs.append({
            "id": f"condition_{cond.lower().replace(' ', '_')}",
            "text": text,
            "metadata": {"entity_type": "condition", "entity_name": cond},
        })

    for med, stats in entity_summaries.get("medications", {}).items():
        top_conds = sorted(stats["condition_dist"].items(), key=lambda x: -x[1])[:3]
        pct = stats["patient_count"] / total * 100
        text = (
            f"Medication: {med}\n\n"
            f"Prescribed to {stats['patient_count']:,} patients ({pct:.1f}% of all patients). "
            f"Average billing for {med} patients: ${stats['avg_billing']:,.2f}.\n"
            f"Primary conditions treated: {', '.join(f'{c} ({n:,})' for c, n in top_conds)}.\n"
            f"Insurance breakdown: {', '.join(f'{i}: {n:,}' for i, n in stats['insurer_dist'].items())}.\n"
            f"Admission types: {', '.join(f'{k}: {v:,}' for k, v in stats['admission_dist'].items())}.\n"
            f"Test results: {', '.join(f'{k}: {v:,}' for k, v in stats['result_dist'].items())}."
        )
        docs.append({
            "id": f"medication_{med.lower().replace(' ', '_')}",
            "text": text,
            "metadata": {"entity_type": "medication", "entity_name": med},
        })

    for ins, stats in entity_summaries.get("insurers", {}).items():
        top_conds = sorted(stats["condition_dist"].items(), key=lambda x: -x[1])[:3]
        top_meds = sorted(stats["medication_dist"].items(), key=lambda x: -x[1])[:3]
        pct = stats["patient_count"] / total * 100
        text = (
            f"Insurance Provider: {ins}\n\n"
            f"Covers {stats['patient_count']:,} patients ({pct:.1f}% of the insured population). "
            f"Average covered patient age: {stats['avg_age']} years. "
            f"Average billing: ${stats['avg_billing']:,.2f}.\n"
            f"Most covered conditions: {', '.join(f'{c} ({n:,})' for c, n in top_conds)}.\n"
            f"Most covered medications: {', '.join(f'{m} ({n:,})' for m, n in top_meds)}.\n"
            f"Admission types: {', '.join(f'{k}: {v:,}' for k, v in stats['admission_dist'].items())}."
        )
        docs.append({
            "id": f"insurer_{ins.lower().replace(' ', '_')}",
            "text": text,
            "metadata": {"entity_type": "insurer", "entity_name": ins},
        })

    conditions = list(entity_summaries.get("conditions", {}).items())
    by_billing = sorted(conditions, key=lambda x: -x[1]["avg_billing"])
    by_stay = sorted(conditions, key=lambda x: -x[1]["avg_stay"])

    top_billing = ", ".join(f"{c} (${s['avg_billing']:,.0f})" for c, s in by_billing[:3])
    low_billing = ", ".join(f"{c} (${s['avg_billing']:,.0f})" for c, s in by_billing[-3:])
    long_stay = ", ".join(f"{c} ({s['avg_stay']} days)" for c, s in by_stay[:3])
    short_stay = ", ".join(f"{c} ({s['avg_stay']} days)" for c, s in by_stay[-3:])
    docs.append({
        "id": "insight_cost_analysis",
        "text": (
            "Healthcare Cost Analysis by Medical Condition\n\n"
            f"Highest average billing: {top_billing}.\n"
            f"Lowest average billing: {low_billing}.\n"
            f"Longest average stay: {long_stay}.\n"
            f"Shortest average stay: {short_stay}."
        ),
        "metadata": {"entity_type": "insight", "entity_name": "cost_analysis"},
    })

    emg_rates = {
        c: s["admission_dist"].get("Emergency", 0) / s["patient_count"] * 100
        for c, s in entity_summaries.get("conditions", {}).items()
    }
    by_emg = sorted(emg_rates.items(), key=lambda x: -x[1])
    docs.append({
        "id": "insight_emergency_rates",
        "text": (
            "Emergency Admission Rates by Condition\n\n"
            f"Highest emergency rates: {', '.join(f'{c} ({r:.1f}%)' for c, r in by_emg[:3])}.\n"
            f"Lowest emergency rates: {', '.join(f'{c} ({r:.1f}%)' for c, r in by_emg[-3:])}."
        ),
        "metadata": {"entity_type": "insight", "entity_name": "emergency_rates"},
    })

    logger.info("Created %d RAG documents", len(docs))
    return docs


def embed_documents(documents: list, embedding_model: str) -> dict:
    """Generate embeddings and return a ChromaDBDataset-compatible dict."""
    from openai import OpenAI

    texts = [doc["text"] for doc in documents]
    ids = [doc["id"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]

    openai_client = OpenAI(api_key=get_openai_api_key())
    logger.info("Generating embeddings for %d documents with %s...", len(texts), embedding_model)
    response = openai_client.embeddings.create(input=texts, model=embedding_model)
    embeddings = [item.embedding for item in response.data]

    logger.info(
        "Embeddings ready: %d vectors of dimension %d — handing off to ChromaDBDataset",
        len(embeddings), len(embeddings[0]) if embeddings else 0,
    )
    return {"documents": texts, "ids": ids, "metadatas": metadatas, "embeddings": embeddings}
