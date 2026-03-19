from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from opik import Opik
from opik.evaluation import evaluate
from opik.evaluation.metrics.score_result import ScoreResult
from pydantic import BaseModel, Field


DATASET_NAME = "evaluations/support_eval_e2e"

EVAL_ITEMS = [
    {
        "input": {"question": "How do I reset my password?"},
        "expected_output": "Click 'Forgot password' on the login page and follow instructions.",
        "metadata": {"difficulty": "easy"},
    },
    {
        "input": {"question": "How can I cancel my subscription?"},
        "expected_output": "You can cancel your subscription from the billing section in settings.",
        "metadata": {"difficulty": "medium"},
    },
]

SUPPORT_PROMPT = (
    "You are a customer support agent. Answer the following question clearly.\n\n"
    "Question: {question}"
)

JUDGE_PROMPT = (
    "You are an expert evaluator for customer support answers.\n\n"
    "Question: {question}\n"
    "Expected Answer: {expected_output}\n"
    "Model Answer: {model_output}\n\n"
    "Score from 1 to 5. Return ONLY a JSON object: {{\"score\": <int>}}"
)


class JudgeScore(BaseModel):
    score: int = Field(description="Integer score between 1 and 5 inclusive.")


def get_or_create_dataset(client: Opik):
    """Get existing dataset or create and seed it from EVAL_ITEMS."""
    dataset = client.get_or_create_dataset(name=DATASET_NAME)

    existing = dataset.get_items()
    if not existing:
        print(f"Seeding dataset '{DATASET_NAME}' with {len(EVAL_ITEMS)} items...")
        dataset.insert(EVAL_ITEMS)
    else:
        print(f"Dataset '{DATASET_NAME}' already has {len(existing)} items.")

    return dataset


def show_dataset_info(dataset):
    """Demonstrate dataset API operations."""
    print("\n--- Dataset info ---")
    print(f"Name:            {dataset.name}")
    print(f"Version:         {dataset.get_current_version_name()}")
    print(f"Tags:            {dataset.get_tags()}")

    items = dataset.get_items()
    print(f"Items:           {len(items)}")

    print("\n--- Items as JSON ---")
    print(dataset.to_json())

    try:
        df = dataset.to_pandas()
        print("\n--- Items as DataFrame ---")
        print(df[["input", "expected_output", "metadata"]].to_string())
    except Exception as e:
        print(f"(to_pandas unavailable: {e})")


def make_support_task(llm: ChatOpenAI):
    def support_task(dataset_item: dict) -> dict:
        question = dataset_item.get("input", {}).get("question", "")
        response = llm.invoke(SUPPORT_PROMPT.format(question=question))
        return {"output": response.content}
    return support_task


def make_judge_scorer(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(JudgeScore)

    def llm_judge_scorer(dataset_item: dict, task_outputs: dict, **kwargs) -> ScoreResult:
        input_ = dataset_item.get("input", {})
        try:
            result = structured_llm.invoke(JUDGE_PROMPT.format(
                question=input_.get("question", ""),
                expected_output=dataset_item.get("expected_output", ""),
                model_output=task_outputs.get("output", ""),
            ))
            return ScoreResult(name="llm_judge_score", value=float(result.score), reason="LLM-based correctness score")
        except Exception as e:
            return ScoreResult(name="llm_judge_score", value=0.0, reason=str(e), scoring_failed=True)

    return llm_judge_scorer


def demonstrate_update(dataset):
    """Update an existing item — requires the full item dict including id."""
    items = dataset.get_items()
    if not items:
        print("(no items to update)")
        return

    # update() requires the full item object, not just the changed fields
    updated = {**items[0], "expected_output": "Updated: go to Settings > Account > Reset Password."}
    dataset.update([updated])
    print(f"Updated item {items[0]['id']} with new expected_output.")

    refreshed = dataset.get_items()
    updated_item = next((i for i in refreshed if i["id"] == items[0]["id"]), None)
    print(f"Confirmed new expected_output: {updated_item['expected_output'] if updated_item else 'not found'}")


def demonstrate_delete(dataset):
    """Delete a specific item by ID — creates a new dataset version."""
    items = dataset.get_items()
    if len(items) < 2:
        print("(need at least 2 items to demo delete safely)")
        return

    target_id = items[-1]["id"]
    dataset.delete([target_id])
    print(f"Deleted item {target_id}.")
    print(f"Items remaining: {len(dataset.get_items())}")


def demonstrate_insert_from_json(dataset):
    """Insert a new item using a raw JSON string instead of a list of dicts."""
    import json

    new_items = [
        {
            "input": {"question": "How do I update my billing information?"},
            "expected_output": "Go to Settings > Billing and update your payment method.",
            "metadata": {"difficulty": "easy"},
        }
    ]
    dataset.insert_from_json(json.dumps(new_items))
    print(f"Inserted via insert_from_json. Items now: {len(dataset.get_items())}")


def main():
    load_dotenv()

    client = Opik()
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0) # Need to export OPENAI_API_KEY in env for this to work

    dataset = get_or_create_dataset(client)
    show_dataset_info(dataset)

    print("\n--- Update ---")
    demonstrate_update(dataset)

    print("\n--- Delete ---")
    demonstrate_delete(dataset)

    print("\n--- Insert from JSON ---")
    demonstrate_insert_from_json(dataset)

    print("\n--- Running experiment ---")
    result = evaluate(
        dataset=dataset,
        task=make_support_task(llm),
        scoring_functions=[make_judge_scorer(llm)],
        experiment_name="support_eval_e2e_v1",
        experiment_config={"model_name": "gpt-4o"},
    )

    scores = [
        sr.value
        for tr in result.test_results
        for sr in tr.score_results
        if not sr.scoring_failed
    ]
    avg = sum(scores) / len(scores) if scores else None
    print(f"\nAverage score: {avg:.2f}" if avg is not None else "\nNo scores recorded.")
    print(f"Results: {result.experiment_url}")

    # clear() deletes all items and creates a new dataset version — run last
    print("\n--- Clear (destructive) ---")
    dataset.clear()
    print(f"Dataset cleared. Items remaining: {len(dataset.get_items())}")


if __name__ == "__main__":
    main()
