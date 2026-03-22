import json
from typing import Any, Callable, Dict, List

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from opik.api_objects.dataset.dataset import Dataset
from opik.api_objects.prompt.text.prompt import Prompt
from opik.evaluation import evaluate
from opik.evaluation.metrics.score_result import ScoreResult
from opik.evaluation.test_result import TestResult
from pydantic import BaseModel, Field


class JudgeScore(BaseModel):
    score: int = Field(
        description="Integer score between 1 and 5 inclusive."
    )


def _prompt_to_template(prompt: Prompt) -> ChatPromptTemplate:
    """Convert an Opik SDK Prompt object to a LangChain ChatPromptTemplate.

    In sdk mode, OpikPromptDataset returns the raw Prompt object instead of a
    ChatPromptTemplate. This helper performs the conversion so node logic stays
    the same regardless of the dataset mode.
    """
    data = prompt.prompt
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return ChatPromptTemplate.from_template(data)
    messages = [(m["role"], m["content"]) for m in data]
    return ChatPromptTemplate.from_messages(messages)


# The Langfuse evaluator receives (input, output, expected_output)
# keyword arguments and returns a Langfuse ``Evaluation`` object. Opik instead
# passes the full ``dataset_item`` dict and a ``task_outputs`` dict, and returns
# an Opik ScoreResult. The scorer is also registered via scoring_functions on
# evaluate() instead of evaluators on dataset.run_experiment()
def init_llm_judge_evaluator(
    judge_llm: ChatOpenAI,
    judge_prompt: Prompt,
) -> Callable:
    """Creates LLM-as-a-Judge scorer function compatible with opik.evaluation.evaluate().
    """
    model_name = getattr(judge_llm, "model_name", None)
    metadata = {"judge_model": model_name} if model_name else None
    structured_judge_llm = judge_llm.with_structured_output(JudgeScore)
    judge_template = _prompt_to_template(judge_prompt)

    def llm_judge_scorer(
        dataset_item: Dict[str, Any],
        task_outputs: Dict[str, Any],
        **kwargs,
    ) -> ScoreResult:
        # Opik passes nested dicts, so we can extract fields manually.
        input_ = dataset_item.get("input", {})
        expected_output = dataset_item.get("expected_output", "")
        output = task_outputs.get("output", "")

        messages: list[BaseMessage] = judge_template.format_messages(
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

        # There is a metadata parameter for ScoreResult actually, 
        # but I don't know where it shows up in the UI 
        return ScoreResult(
            name="llm_judge_score",
            value=float(score),
            reason=reason,
            metadata=metadata,
        )

    return llm_judge_scorer


def make_support_task(
    support_prompt: Prompt,
    support_llm: ChatOpenAI,
    opik_client: Any,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Creates support-answer task callable compatible with opik.evaluation.evaluate().

    The returned callable follows the LLMTask type expected by Opik: it receives a
    dataset item dict and returns a dict with an ``output`` key.
    """
    support_template = _prompt_to_template(support_prompt)

    def support_task(dataset_item: Dict[str, Any]) -> Dict[str, Any]:
        question = dataset_item.get("input", {}).get("question", "")

        # Opik can use a standard LangChain ChatPromptTemplate, so format_messages()
        # is used instead of manually formatting strings.
        messages = support_template.format_messages(question=question)

        # OpikTracer is passed as a callback so Opik captures the trace automatically.
        response = support_llm.invoke(
            messages,
            config={"callbacks": [opik_client]},
        )

        # Instead of returning a string like Langfuse does, Opik tasks must return a dict
        return {"output": response.content}

    return support_task


def _pass_rate(test_results: List[TestResult]) -> ScoreResult:
    """Compute the fraction of items that scored 4 or above."""
    scores = [
        sr.value
        for tr in test_results
        for sr in tr.score_results
        if not sr.scoring_failed
    ]
    rate = sum(1 for s in scores if s >= 4) / len(scores) if scores else 0.0
    return ScoreResult(name="pass_rate", value=rate)


def run_experiment(
    eval_ds: Dataset,
    support_task: Callable,
    llm_judge_evaluator: Callable,
    support_prompt: Prompt,
    model_name: str,
) -> None:
    """Run an Opik evaluation experiment over the dataset.

    In sdk mode, the Prompt object carries a ``commit`` attribute that uniquely
    identifies the prompt version, equivalent to Langfuse's integer version.
    """
    prompt_commit = support_prompt.commit
    experiment_name = f"support_eval_prompt_{prompt_commit[:8]}"

    evaluate(
        dataset=eval_ds,
        task=support_task,
        scoring_functions=[llm_judge_evaluator],  # Langfuse calls this parameter "evaluators"
        experiment_name=experiment_name,
        experiment_config={
            "prompt_commit": prompt_commit,
            "model_name": model_name,
        },
        experiment_scoring_functions=[_pass_rate],
    )

