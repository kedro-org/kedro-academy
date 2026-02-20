from dotenv import load_dotenv
from langfuse import get_client
from langfuse import Evaluation
from langfuse.openai import OpenAI
from openai import OpenAI as RawOpenAI


eval_dataset = [
    {
        "input": "How can I reset my password?",
        "expected_output": "Click 'Forgot password' on the login page and follow instructions."
    },
    {
        "input": "How do I cancel my subscription?",
        "expected_output": "You can cancel your subscription from the billing section in settings."
    }
]


def support_prompt_v1(question: str) -> str:
    return f"Answer the support question:\n{question}"


def support_prompt_v2(question: str) -> str:
    return f"""
You are a professional and concise support assistant.
Provide a direct and helpful answer.

Question:
{question}
"""


def main():
    load_dotenv()

    langfuse = get_client()

    # Wrapped OpenAI client (auto-logs traces to Langfuse)
    lf_openai = OpenAI()
    # Raw OpenAI client (for judge if you want separate control)
    judge_client = RawOpenAI()

    def make_task(prompt_fn, model_name):
        def task(*, item, **kwargs):
            question = item["input"]

            prompt_text = prompt_fn(question)

            response = lf_openai.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0
            )

            return response.choices[0].message.content

        return task

    def quality_evaluator(*, input, output, expected_output, metadata, **kwargs):
        judge_prompt = f"""
    You are grading a support chatbot answer.

    Question: {input}
    Expected Answer: {expected_output}
    Model Answer: {output}

    Score from 1 to 5 for correctness and relevance.
    Return only a number.
    """

        response = judge_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0
        )

        score = int(response.choices[0].message.content.strip())

        return Evaluation(
            name="quality_score",
            value=score,
            comment="LLM-graded correctness and relevance"
        )

    result_v1 = langfuse.run_experiment(
        name="support_eval_v1_prompt_v1",
        description="Support QA evaluation - prompt v1",
        data=eval_dataset,
        task=make_task(support_prompt_v1, model_name="gpt-4o-mini"),
        evaluators=[quality_evaluator],
        metadata={
            "prompt_name": "support_prompt",
            "prompt_version": "v1",
            "model": "gpt-4o-mini",
            "dataset": "support_eval_local_v1"
        }
    )

    print(result_v1.format())

    result_v2 = langfuse.run_experiment(
        name="support_eval_v1_prompt_v2",
        description="Support QA evaluation - prompt v2",
        data=eval_dataset,
        task=make_task(support_prompt_v2, model_name="gpt-4o-mini"),
        evaluators=[quality_evaluator],
        metadata={
            "prompt_name": "support_prompt",
            "prompt_version": "v2",
            "model": "gpt-4o-mini",
            "dataset": "support_eval_local_v1"
        }
    )

    print(result_v2.format())


if __name__ == "__main__":
    main()
