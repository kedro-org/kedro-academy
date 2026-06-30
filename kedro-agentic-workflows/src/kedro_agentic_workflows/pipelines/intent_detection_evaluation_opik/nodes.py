import logging
from typing import Any, Callable

from kedro.pipeline import LLMContext
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from opik import Dataset
from opik.evaluation import evaluate
from opik.evaluation.metrics.score_result import ScoreResult  # no public re-export
from pydantic import BaseModel, Field

from ..intent_detection.agent import IntentDetectionAgent

logger = logging.getLogger(__name__)


class JudgeScore(BaseModel):
    score: int = Field(description="Integer score between 1 and 5 inclusive.")


def init_reason_judge_evaluator(
    intent_judge_llm: ChatOpenAI,
    judge_llm_prompt: ChatPromptTemplate,
) -> Callable:
    """Creates LLM-as-a-Judge scorer compatible with opik.evaluation.evaluate()."""
    model_name = getattr(intent_judge_llm, "model_name", None)
    metadata = {"judge_model": model_name} if model_name else None
    structured_judge_llm = intent_judge_llm.with_structured_output(JudgeScore)

    def reason_judge_evaluator(
        dataset_item: dict[str, Any],
        task_outputs: dict[str, Any],
        **kwargs,
    ) -> ScoreResult:
        input_ = dataset_item.get("input", {})
        expected_output = dataset_item.get("expected_output", {})

        messages: list[BaseMessage] = judge_llm_prompt.format_messages(
            question=input_.get("question", ""),
            predicted_intent=task_outputs.get("intent", ""),
            predicted_reason=task_outputs.get("reason", ""),
            expected_intent=expected_output.get("intent", ""),
            expected_reason=expected_output.get("reason", ""),
        )

        try:
            result: JudgeScore = structured_judge_llm.invoke(messages)
            score = float(result.score)
            reason = "LLM judge evaluation of reasoning quality"
            result_metadata = metadata
        except Exception as e:
            # Judge failed: emit the lowest valid score (1, not 0 which is off
            # the 1-5 scale) and flag it so downstream analysis can filter it.
            score = 1.0
            reason = f"Evaluator failed: {e}"
            result_metadata = {**(metadata or {}), "evaluation_failed": True}

        return ScoreResult(
            name="reason_quality",
            value=score,
            reason=reason,
            metadata=result_metadata,
        )

    return reason_judge_evaluator


def init_intent_accuracy_evaluator() -> Callable:
    """Creates exact-match intent accuracy scorer compatible with opik.evaluation.evaluate()."""

    def intent_accuracy_evaluator(
        dataset_item: dict[str, Any],
        task_outputs: dict[str, Any],
        **kwargs,
    ) -> ScoreResult:
        predicted = task_outputs.get("intent", "")
        expected = dataset_item.get("expected_output", {}).get("intent", "")
        score = 1.0 if predicted == expected else 0.0

        return ScoreResult(
            name="intent_accuracy",
            value=score,
            reason=f"predicted={predicted}, expected={expected}",
        )

    return intent_accuracy_evaluator


def make_intent_detection_task(
    intent_detection_context: LLMContext,
    opik_tracer: Any,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Creates intent detection task callable compatible with opik.evaluation.evaluate().

    The returned callable follows the LLMTask type expected by Opik: receives a
    dataset item dict and returns a dict with the task outputs.
    """
    agent = IntentDetectionAgent(context=intent_detection_context)
    agent.compile()

    def intent_agent_task(dataset_item: dict[str, Any]) -> dict[str, Any]:
        question = dataset_item.get("input", {}).get("question", "")
        item_id = dataset_item.get("id", "unknown")

        agent_input = {
            "messages": [HumanMessage(content=question)],
            "user_context": {},
        }

        try:
            result = agent.invoke(
                agent_input,
                {
                    "configurable": {"thread_id": item_id},
                    "callbacks": [opik_tracer],
                },
            )
        except Exception as e:
            # Don't let one failing item crash the whole experiment; log it and
            # return an empty result (scores as a miss) so evaluate() continues.
            logger.error("Intent detection failed for item %s: %s", item_id, e)
            return {"intent": "", "reason": ""}

        return {
            "intent": result.get("intent", ""),
            "reason": result.get("reason", ""),
        }

    return intent_agent_task


def run_experiment(
    intent_evaluation_data: Dataset,
    intent_agent_task: Callable,
    intent_accuracy_evaluator: Callable,
    reason_judge_evaluator: Callable,
    intent_prompt_version: int,
    model_name: str,
) -> None:
    """Run an Opik evaluation experiment over the intent detection dataset.

    The experiment name mirrors the Langfuse variant
    (``intent_prompt_v{version}_model_{model}``) so runs are comparable across
    providers in either UI.
    """
    experiment_name = f"intent_prompt_v{intent_prompt_version}_model_{model_name}"

    evaluate(
        dataset=intent_evaluation_data,
        task=intent_agent_task,
        scoring_functions=[intent_accuracy_evaluator, reason_judge_evaluator],
        experiment_name=experiment_name,
        experiment_config={
            "prompt_version": intent_prompt_version,
            "model_name": model_name,
        },
    )

    # evaluate() prints its own score summary; log completion to match Langfuse.
    logger.info("Experiment '%s' completed. See results in the Opik UI.", experiment_name)
