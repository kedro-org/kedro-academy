from typing import Callable, Dict, Any

from langfuse._client.datasets import DatasetClient


def init_llm_judge_evaluator(
    judge_llm,
    llm_judge_evaluator_prompt,
) -> Callable[[Dict[str, Any], str, str], float]:
    """
    Initialize LLM-as-a-Judge evaluator.

    Args:
        judge_llm: Configured LangChain ChatOpenAI model
        llm_judge_evaluator_prompt: LangChain ChatPromptTemplate

    Returns:
        Callable evaluator(input, output, expected_output) -> float
    """

    def llm_judge_evaluator(
        input: Dict[str, Any],
        output: str,
        expected_output: str,
        metadata,
        **kwargs
    ) -> float:
        compiled_prompt = llm_judge_evaluator_prompt.compile(
            question=input["question"],
            model_output=output,
            expected_output=expected_output,
        )

        response = judge_llm.invoke(compiled_prompt)
        raw_score = response.content.strip()

        try:
            score = float(raw_score)
        except ValueError:
            # Fallback in case model misbehaves
            score = 0.0

        return score

    return llm_judge_evaluator


def make_support_task(support_answer_prompt, support_answer_llm, langfuse_client, model_name: str = "gpt-4o"):
    def support_task(*, item, **kwargs):
        question = item.input["question"]

        compiled_prompt = support_answer_prompt.compile(question=question)

        with langfuse_client.start_as_current_observation(
            name="support_answer_generation",
            as_type="generation",
            model=model_name,
            input=compiled_prompt,
            prompt=support_answer_prompt,
        ) as generation:
            response = support_answer_llm.invoke(compiled_prompt)
            output = response.content

            generation.update(output=output)

        return output

    return support_task


def run_experiment(eval_ds: DatasetClient, support_task: Callable, llm_judge_evaluator: Callable):
    print("---")
    print(type(eval_ds))
    print("---")
    result_v1 = eval_ds.run_experiment(
        name="support_eval_prompt_v1",
        task=support_task,
        evaluators=[llm_judge_evaluator],
        metadata={
            "model": "gpt-4o",
            "description": "kedro-evaluation"
        }
    )

    print(result_v1.format())
