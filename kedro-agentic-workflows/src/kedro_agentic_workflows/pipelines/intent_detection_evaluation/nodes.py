import logging
from typing import Any, Callable

from kedro.pipeline import LLMContext
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langfuse import Evaluation, Langfuse
from langfuse._client.datasets import DatasetClient
from pydantic import BaseModel, Field

from ..intent_detection.agent import IntentDetectionAgent


class JudgeScore(BaseModel):
    score: int = Field(
        description="Integer score between 1 and 5 inclusive."
    )


def init_reason_judge_evaluator(
    intent_judge_llm: ChatOpenAI,
    intent_judge_prompt: ChatPromptTemplate,
) -> Callable[..., Evaluation]:
    """
    Creates LLM-as-a-Judge evaluator compatible with Langfuse experiments.
    """

    model_name = getattr(intent_judge_llm, "model_name", None)
    metadata = {"judge_model": model_name} if model_name else None
    structured_judge_llm = intent_judge_llm.with_structured_output(JudgeScore)

    def reason_judge_evaluator(
        input: dict[str, Any],
        output: dict[str, Any],
        expected_output: dict[str, Any],
        **kwargs,
    ) -> Evaluation:

        messages: list[BaseMessage] = intent_judge_prompt.format_messages(
            question=input.get("question", ""),
            predicted_intent=output.get("intent", ""),
            predicted_reason=output.get("reason", ""),
            expected_intent=expected_output.get("intent", ""),
            expected_reason=expected_output.get("reason", ""),
        )

        try:
            result: JudgeScore = structured_judge_llm.invoke(messages)
            score = result.score

        except Exception as e:
            return Evaluation(
                name="reason_quality",
                value=0,
                comment=f"Evaluator failed: {str(e)}",
                metadata=metadata,
            )

        return Evaluation(
            name="reason_quality",
            value=score,
            comment="LLM judge evaluation of reasoning quality",
            metadata=metadata,
        )

    return reason_judge_evaluator


def init_intent_accuracy_evaluator() -> Callable[..., Evaluation]:
    def intent_accuracy_evaluator(
        input: dict[str, Any],
        output: dict[str, Any],
        expected_output: dict[str, Any],
        **kwargs,
    ) -> Evaluation:

        predicted = output.get("intent", "")
        expected = expected_output.get("intent", "")

        score = 1 if predicted == expected else 0

        return Evaluation(
            name="intent_accuracy",
            value=score,
            comment=f"predicted={predicted}, expected={expected}",
        )

    return intent_accuracy_evaluator


def make_intent_detection_task(
    intent_detection_context: LLMContext,
    langfuse_client: Langfuse,
) -> Callable[..., dict[str, Any]]:
    """
    Creates support task callable compatible with Langfuse Dataset experiment.
    """
    agent = IntentDetectionAgent(context=intent_detection_context)
    agent.compile()
    model_name = getattr(agent.context.llm, "model_name", "unknown-model")

    def intent_agent_task(*, item, **kwargs) -> dict[str, Any]:
        question = item.input.get("question", "")

        agent_input = {
            "messages": [
                HumanMessage(content=question),
            ],
            "user_context": {},
        }

        with langfuse_client.start_as_current_observation(
            name="intent_detection_agent",
            as_type="generation",
            model=model_name,
            input={"question": question},
            # TODO: it has to be langfuse prompt object or name (?)
            # prompt=agent.context.prompts["intent_prompt_langfuse"],
        ) as generation:

            try:
                result = agent.invoke(agent_input, {"configurable": {"thread_id": "1"}})
                intent = result.get("intent", "")
                reason = result.get("reason", "")

                output = {
                    "intent": intent,
                    "reason": reason,
                }
            except Exception as e:
                output = {
                    "intent": "",
                    "reason": "",
                }

                generation.update(
                    output=output,
                    metadata={"error": str(e)}
                )
                raise

            generation.update(
                output=output,
                metadata={"intent": intent},
            )

        return output

    return intent_agent_task


def run_experiment(
    intent_evaluation_data: DatasetClient,
    intent_agent_task: Callable,
    intent_accuracy_evaluator: Callable,
    reason_judge_evaluator: Callable,
    intent_prompt_version: int,
    model_name: str
) -> None:
    experiment_name = f"intent_prompt_v{intent_prompt_version}_model_{model_name}"

    result = intent_evaluation_data.run_experiment(
        name=experiment_name,
        task=intent_agent_task,
        evaluators=[intent_accuracy_evaluator, reason_judge_evaluator],
        metadata={
            "prompt_version": intent_prompt_version,
            "model_name": model_name
        },
    )

    formatted = result.format().replace("\\n", "\n")
    logger.info(
        "Experiment '%s' completed.\n\n%s", experiment_name, formatted
    )
