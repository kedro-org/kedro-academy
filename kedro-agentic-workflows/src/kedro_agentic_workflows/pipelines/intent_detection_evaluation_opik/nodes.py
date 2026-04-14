import json
import logging
from typing import Any, Callable

from kedro.pipeline import LLMContext
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from opik.api_objects.dataset.dataset import Dataset
from opik.api_objects.prompt.text.prompt import Prompt
from opik.evaluation import evaluate
from opik.evaluation.metrics.score_result import ScoreResult
from pydantic import BaseModel, Field

from ..intent_detection.agent import IntentDetectionAgent

logger = logging.getLogger(__name__)


class JudgeScore(BaseModel):
    score: int = Field(description="Integer score between 1 and 5 inclusive.")


def _prompt_to_template(prompt: Prompt) -> ChatPromptTemplate:
    """Convert an Opik SDK Prompt object to a LangChain ChatPromptTemplate."""
    data = prompt.prompt
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return ChatPromptTemplate.from_template(data)
    messages = [(m["role"], m["content"]) for m in data]
    return ChatPromptTemplate.from_messages(messages)


def init_reason_judge_evaluator(
    intent_judge_llm: ChatOpenAI,
    intent_judge_prompt: Prompt,
) -> Callable:
    """Creates LLM-as-a-Judge scorer compatible with opik.evaluation.evaluate()."""
    model_name = getattr(intent_judge_llm, "model_name", None)
    metadata = {"judge_model": model_name} if model_name else None
    structured_judge_llm = intent_judge_llm.with_structured_output(JudgeScore)
    judge_template = _prompt_to_template(intent_judge_prompt)

    def reason_judge_evaluator(
        dataset_item: dict[str, Any],
        task_outputs: dict[str, Any],
        **kwargs,
    ) -> ScoreResult:
        input_ = dataset_item.get("input", {})
        expected_output = dataset_item.get("expected_output", {})

        messages: list[BaseMessage] = judge_template.format_messages(
            question=input_.get("question", ""),
            predicted_intent=task_outputs.get("intent", ""),
            predicted_reason=task_outputs.get("reason", ""),
            expected_intent=expected_output.get("intent", ""),
            expected_reason=expected_output.get("reason", ""),
        )

        try:
            result: JudgeScore = structured_judge_llm.invoke(messages)
            score = result.score
            reason = "LLM judge evaluation of reasoning quality"
        except Exception as e:
            score = 0
            reason = f"Evaluator failed: {str(e)}"

        return ScoreResult(
            name="reason_quality",
            value=float(score),
            reason=reason,
            metadata=metadata,
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

        result = agent.invoke(
            agent_input,
            {
                "configurable": {"thread_id": item_id},
                "callbacks": [opik_tracer],
            },
        )

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
    intent_judge_prompt: Prompt,
    model_name: str,
) -> None:
    """Run an Opik evaluation experiment over the intent detection dataset."""
    prompt_commit = intent_judge_prompt.commit
    experiment_name = f"intent_eval_prompt_{prompt_commit[:8]}_model_{model_name}"

    evaluate(
        dataset=intent_evaluation_data,
        task=intent_agent_task,
        scoring_functions=[intent_accuracy_evaluator, reason_judge_evaluator],
        experiment_name=experiment_name,
        experiment_config={
            "prompt_commit": prompt_commit,
            "model_name": model_name,
        },
    )
