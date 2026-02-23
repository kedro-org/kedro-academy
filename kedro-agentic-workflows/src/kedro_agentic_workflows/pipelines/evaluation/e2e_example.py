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

    lf_openai = OpenAI()
    judge_client = RawOpenAI()

    def make_support_task(prompt_version: int):
        def support_task(*, item, **kwargs):
            question = item.input["question"]

            # Fetch specific prompt version
            prompt = langfuse.get_prompt(
                "support_answer",
                version=prompt_version
            )

            compiled_prompt = prompt.compile(
                question=question
            )

            response = lf_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=compiled_prompt,
                temperature=0,
            )

            return response.choices[0].message.content

        return support_task

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

    Score from 1 to 5.
    Return ONLY a number.
    """

        response = judge_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0
        )

        try:
            score = int(response.choices[0].message.content.strip())
        except:
            score = 0

        return Evaluation(
            name="llm_judge_score",
            value=score,
            comment="LLM-based correctness score"
        )

    # ----------------------------
    # Run Experiment with Prompt Version 1
    # ----------------------------
    result_v1 = dataset.run_experiment(
        name="support_eval_prompt_v1",
        task=make_support_task(prompt_version=1),
        evaluators=[llm_judge_evaluator],
        metadata={
            "model": "gpt-4o-mini",
            "prompt_version": 1
        }
    )

    print(result_v1.format())

    # ----------------------------
    # Run Experiment with Prompt Version 2
    # ----------------------------
    result_v2 = dataset.run_experiment(
        name="support_eval_prompt_v2",
        task=make_support_task(prompt_version=2),
        evaluators=[llm_judge_evaluator],
        metadata={
            "model": "gpt-4o-mini",
            "prompt_version": 2
        }
    )

    print(result_v2.format())


if __name__ == "__main__":
    main()
