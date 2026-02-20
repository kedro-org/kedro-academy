from typing import Any

from dotenv import load_dotenv
from langfuse import get_client
from langfuse import Evaluation
from langfuse.openai import OpenAI
from openai import OpenAI as RawOpenAI


eval_dataset = [
    {
        "input": {"question": "How do I reset my password?"},
        "expected_output": "Click 'Forgot password' on the login page and follow instructions.",
        "metadata": {"difficulty": "easy"}
    },
    {
        "input": {"question": "How can I cancel my subscription?"},
        "expected_output": "You can cancel your subscription from the billing section in settings.",
        "metadata": {"difficulty": "medium"}
    }
]


def create_dataset(ds: list[dict[str, Any]], name: str, client, description: str = "Support QA evaluation dataset v1"):
    try:
        dataset = client.get_dataset(name=name)
        print(f"Dataset '{name}' already exists.")
        return dataset

    except Exception:
        print(f"Creating dataset '{name}'...")
        dataset = client.create_dataset(
            name=name,
            description=description,
        )

        for item in ds:
            item_to_add = {"dataset_name": name, **item}
            client.create_dataset_item(**item_to_add)

        return dataset


def main():
    load_dotenv()
    langfuse = get_client()

    dataset = create_dataset(eval_dataset, "evaluations/support_eval_v1", langfuse)

    # Wrapped OpenAI client (auto-logs traces to Langfuse)
    lf_openai = OpenAI()
    # Raw OpenAI client (for judge if you want separate control)
    judge_client = RawOpenAI()

    def support_task(*, item, **kwargs):
        question = item.input["question"]

        response = lf_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"Answer this support question clearly and concisely:\n{question}"
                }
            ],
            temperature=0
        )

        return response.choices[0].message.content

    def llm_judge_evaluator(
        *,
        input,
        output,
        expected_output,
        metadata,
        **kwargs
    ):
        judge_prompt = f"""
    You are an expert evaluator for customer support answers.

    Question:
    {input['question']}

    Expected Answer:
    {expected_output}

    Model Answer:
    {output}

    Evaluate correctness and helpfulness.
    Score from 1 to 5.

    Return ONLY a number.
    """

        response = judge_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0
        )

        score = int(response.choices[0].message.content.strip())

        return Evaluation(
            name="llm_judge_score",
            value=score,
            comment="LLM-based correctness & helpfulness score (1-5)"
        )

    result = dataset.run_experiment(
        name="support_eval_llm_judge_v1",
        description="Support evaluation using LLM-as-a-Judge",
        task=support_task,
        evaluators=[llm_judge_evaluator],
        metadata={
            "model_under_test": "gpt-4o-mini",
            "judge_model": "gpt-4o-mini",
            "prompt_version": "v1"
        }
    )

    print(result.format())

    # result_v2 = langfuse.run_experiment(
    #     name="support_eval_v1_prompt_v2",
    #     description="Support QA evaluation - prompt v2",
    #     data=eval_dataset,
    #     task=make_task(support_prompt_v2, model_name="gpt-4o-mini"),
    #     evaluators=[quality_evaluator],
    #     metadata={
    #         "prompt_name": "support_prompt",
    #         "prompt_version": "v2",
    #         "model": "gpt-4o-mini",
    #         "dataset": "support_eval_local_v1"
    #     }
    # )
    #
    # print(result_v2.format())


if __name__ == "__main__":
    main()
