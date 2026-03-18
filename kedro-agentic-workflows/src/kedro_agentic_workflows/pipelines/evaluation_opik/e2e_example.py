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


def main():
    load_dotenv()

    client = Opik()
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0) # Need to export OPENAI_API_KEY in env for this to work

    dataset = get_or_create_dataset(client)
    show_dataset_info(dataset)

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


if __name__ == "__main__":
    main()
