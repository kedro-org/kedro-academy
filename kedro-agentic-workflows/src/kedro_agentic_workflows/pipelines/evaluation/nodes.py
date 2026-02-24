from typing import Callable, Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langfuse import Evaluation, Langfuse
from langfuse._client.datasets import DatasetClient
from langfuse.model import ChatPromptClient
from pydantic import BaseModel, Field


class JudgeScore(BaseModel):
    score: int = Field(
        description="Integer score between 1 and 5 inclusive."
    )


def init_llm_judge_evaluator(
    judge_llm: ChatOpenAI,
    judge_prompt: ChatPromptTemplate,
) -> Callable[..., Evaluation]:
    """
    Creates LLM-as-a-Judge evaluator compatible with Langfuse experiments.
    """

    model_name = getattr(judge_llm, "model_name", "unknown-model")
    structured_judge_llm = judge_llm.with_structured_output(JudgeScore)

    def llm_judge_evaluator(
        input: Dict[str, Any],
        output: str,
        expected_output: str,
        **kwargs,
    ) -> Evaluation:

        messages: list[BaseMessage] = judge_prompt.format_messages(
            question=input.get("question", ""),
            model_output=output,
            expected_output=expected_output,
        )

        try:
            result: JudgeScore = structured_judge_llm.invoke(messages)
            score = result.score
        except Exception as e:
            return Evaluation(
                name="llm_judge_score",
                value=0.0,
                comment=f"Evaluator failed: {str(e)}",
                metadata={"judge_model": model_name},
            )

        return Evaluation(
            name="llm_judge_score",
            value=score,
            comment="LLM-based correctness score",
            metadata={"judge_model": model_name},
        )

    return llm_judge_evaluator


def make_support_task(
    support_prompt: ChatPromptClient,
    support_llm: ChatOpenAI,
    langfuse_client: Langfuse,
) -> Callable[..., str]:
    """
    Creates support task callable compatible with Langfuse Dataset experiment.
    """

    model_name = getattr(support_llm, "model_name", "unknown-model")

    def support_task(*, item, **kwargs) -> str:
        question = item.input.get("question", "")

        compiled_prompt = support_prompt.compile(question=question)

        with langfuse_client.start_as_current_observation(
            name="support_answer_generation",
            as_type="generation",
            model=model_name,
            input=compiled_prompt,
            prompt=support_prompt,
        ) as generation:

            try:
                response = support_llm.invoke(compiled_prompt)
                output = response.content
            except Exception as e:
                output = ""
                generation.update(
                    output=output,
                    metadata={"error": str(e)}
                )
                raise

            generation.update(output=output)

        return output

    return support_task


def run_experiment(
    eval_ds: DatasetClient,
    support_task: Callable,
    llm_judge_evaluator: Callable,
    support_prompt_version: int,
) -> None:

    experiment_name = f"support_eval_prompt_v{support_prompt_version}"

    result = eval_ds.run_experiment(
        name=experiment_name,
        task=support_task,
        evaluators=[llm_judge_evaluator],
        metadata={
            "prompt_version": support_prompt_version,
        },
    )

    print(result.format())
