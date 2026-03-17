from typing import Any, Callable, Dict

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from opik.api_objects.dataset.dataset import Dataset
from opik.evaluation import evaluate
from opik.evaluation.metrics.score_result import ScoreResult
from pydantic import BaseModel, Field


class JudgeScore(BaseModel):
    score: int = Field(
        description="Integer score between 1 and 5 inclusive."
    )


def init_llm_judge_evaluator(
    judge_llm: ChatOpenAI,
    judge_prompt: ChatPromptTemplate,
) -> Callable:
    """Creates LLM-as-a-Judge scorer function compatible with opik.evaluation.evaluate().

    The returned callable follows the ScorerFunction protocol expected by Opik:
    it receives ``dataset_item`` and ``task_outputs`` dicts and returns a ScoreResult.
    """
    structured_judge_llm = judge_llm.with_structured_output(JudgeScore)

    def llm_judge_scorer(
        dataset_item: Dict[str, Any],
        task_outputs: Dict[str, Any],
        **kwargs,
    ) -> ScoreResult:
        input_ = dataset_item.get("input", {})
        expected_output = dataset_item.get("expected_output", "")
        output = task_outputs.get("output", "")

        messages: list[BaseMessage] = judge_prompt.format_messages(
            question=input_.get("question", ""),
            model_output=output,
            expected_output=expected_output,
        )

        try:
            result: JudgeScore = structured_judge_llm.invoke(messages)
            score = result.score
            reason = "LLM-based correctness score"
        except Exception as e:
            score = 0
            reason = f"Evaluator failed: {str(e)}"

        return ScoreResult(
            name="llm_judge_score",
            value=float(score),
            reason=reason,
        )

    return llm_judge_scorer


def make_support_task(
    support_prompt: ChatPromptTemplate,
    support_llm: ChatOpenAI,
    opik_client: Any,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Creates support-answer task callable compatible with opik.evaluation.evaluate().

    The returned callable follows the LLMTask type expected by Opik: it receives a
    dataset item dict and returns a dict with an ``output`` key.

    The ``opik_client`` (OpikTracer LangChain callback) is passed to LangChain's
    invoke so that traces are logged to Opik automatically.
    """

    def support_task(dataset_item: Dict[str, Any]) -> Dict[str, Any]:
        question = dataset_item.get("input", {}).get("question", "")
        messages = support_prompt.format_messages(question=question)

        response = support_llm.invoke(
            messages,
            config={"callbacks": [opik_client]},
        )

        return {"output": response.content}

    return support_task


def run_experiment(
    eval_ds: Dataset,
    support_task: Callable,
    llm_judge_evaluator: Callable,
    support_prompt_version: int,
) -> None:
    """Run an Opik evaluation experiment over the dataset.

    Calls opik.evaluation.evaluate(), which iterates over dataset items, runs the
    task, scores outputs with the evaluator, and logs results to Opik.
    """
    experiment_name = f"support_eval_prompt_v{support_prompt_version}"

    result = evaluate(
        dataset=eval_ds,
        task=support_task,
        scoring_functions=[llm_judge_evaluator],
        experiment_name=experiment_name,
        experiment_config={"prompt_version": support_prompt_version},
    )

    print(result)
