"""Data ingestion pipeline nodes."""
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Name"] = df["Name"].str.title()
    df["Date of Admission"] = pd.to_datetime(df["Date of Admission"])
    df["Discharge Date"] = pd.to_datetime(df["Discharge Date"])
    df["Length of Stay"] = (df["Discharge Date"] - df["Date of Admission"]).dt.days
    for col in ["Medical Condition", "Medication", "Insurance Provider",
                "Admission Type", "Test Results", "Blood Type", "Gender"]:
        df[col] = df[col].str.strip()
    logger.info("Cleaned %d records. Avg stay: %.1f days", len(df), df["Length of Stay"].mean())
    return df


def extract_entity_summaries(df: pd.DataFrame) -> dict:
    total = len(df)
    summaries: dict = {}

    summaries["conditions"] = {
        cond: {
            "type": "condition",
            "patient_count": len(sub := df[df["Medical Condition"] == cond]),
            "avg_age": round(sub["Age"].mean(), 1),
            "avg_billing": round(sub["Billing Amount"].mean(), 2),
            "avg_stay": round(sub["Length of Stay"].mean(), 1),
            "medication_dist": sub["Medication"].value_counts().to_dict(),
            "insurer_dist": sub["Insurance Provider"].value_counts().to_dict(),
            "admission_dist": sub["Admission Type"].value_counts().to_dict(),
            "result_dist": sub["Test Results"].value_counts().to_dict(),
            "blood_type_dist": sub["Blood Type"].value_counts().to_dict(),
            "gender_dist": sub["Gender"].value_counts().to_dict(),
        }
        for cond in df["Medical Condition"].unique()
    }

    summaries["medications"] = {
        med: {
            "type": "medication",
            "patient_count": len(sub := df[df["Medication"] == med]),
            "avg_billing": round(sub["Billing Amount"].mean(), 2),
            "condition_dist": sub["Medical Condition"].value_counts().to_dict(),
            "insurer_dist": sub["Insurance Provider"].value_counts().to_dict(),
            "admission_dist": sub["Admission Type"].value_counts().to_dict(),
            "result_dist": sub["Test Results"].value_counts().to_dict(),
        }
        for med in df["Medication"].unique()
    }

    summaries["insurers"] = {
        ins: {
            "type": "insurer",
            "patient_count": len(sub := df[df["Insurance Provider"] == ins]),
            "avg_billing": round(sub["Billing Amount"].mean(), 2),
            "avg_age": round(sub["Age"].mean(), 1),
            "condition_dist": sub["Medical Condition"].value_counts().to_dict(),
            "medication_dist": sub["Medication"].value_counts().to_dict(),
            "admission_dist": sub["Admission Type"].value_counts().to_dict(),
            "result_dist": sub["Test Results"].value_counts().to_dict(),
        }
        for ins in df["Insurance Provider"].unique()
    }

    summaries["blood_types"] = {
        bt: {
            "type": "blood_type",
            "patient_count": len(sub := df[df["Blood Type"] == bt]),
            "avg_age": round(sub["Age"].mean(), 1),
            "avg_billing": round(sub["Billing Amount"].mean(), 2),
            "condition_dist": sub["Medical Condition"].value_counts().to_dict(),
        }
        for bt in df["Blood Type"].unique()
    }

    summaries["admission_types"] = {
        adm: {
            "type": "admission_type",
            "patient_count": len(sub := df[df["Admission Type"] == adm]),
            "avg_billing": round(sub["Billing Amount"].mean(), 2),
            "avg_stay": round(sub["Length of Stay"].mean(), 1),
            "condition_dist": sub["Medical Condition"].value_counts().to_dict(),
        }
        for adm in df["Admission Type"].unique()
    }

    summaries["test_results"] = {
        res: {
            "type": "test_result",
            "patient_count": len(sub := df[df["Test Results"] == res]),
            "avg_billing": round(sub["Billing Amount"].mean(), 2),
            "condition_dist": sub["Medical Condition"].value_counts().to_dict(),
        }
        for res in df["Test Results"].unique()
    }

    summaries["_total_patients"] = total
    logger.info(
        "Entity summaries: %d conditions, %d medications, %d insurers, %d blood types",
        len(summaries["conditions"]), len(summaries["medications"]),
        len(summaries["insurers"]), len(summaries["blood_types"]),
    )
    return summaries


def store_entity_stats(entity_summaries: dict) -> pd.DataFrame:
    """Flatten entity summaries into a tabular DataFrame for relational storage."""
    Path("data/07_model_output").mkdir(parents=True, exist_ok=True)

    rows = []
    for category in ["conditions", "medications", "insurers", "blood_types", "admission_types", "test_results"]:
        for name, stats in entity_summaries.get(category, {}).items():
            rows.append({
                "entity_name": name,
                "entity_type": stats.get("type", category),
                "patient_count": stats.get("patient_count", 0),
                "avg_billing": stats.get("avg_billing"),
                "avg_age": stats.get("avg_age"),
                "avg_stay": stats.get("avg_stay"),
            })

    df = pd.DataFrame(rows).sort_values("patient_count", ascending=False).reset_index(drop=True)
    logger.info("Prepared %d entity rows for SQLite storage", len(df))
    return df
