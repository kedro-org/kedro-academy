import time

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from kedro_datasets_experimental.opik import OpikTraceDataset


def run_sdk():
    """Test SDK mode using OpikTraceDataset."""
    dataset = OpikTraceDataset(
        credentials={
            "api_key": "",
            "workspace": "",
            "project_name": "kedro-test"
        },
        mode="sdk"
    )

    client = dataset.load()

    @client.track(name="my_sample_workflow")
    def my_workflow(x: int, y: int) -> int:
        time.sleep(0.1)
        return x + y

    result = my_workflow(3, 4)
    print("SDK mode result:", result)


def run_openai():
    """Test OpenAI mode using OpikTraceDataset."""
    dataset = OpikTraceDataset(
        credentials={
            "api_key": "",
            "workspace": "",
            "openai": {
                "openai_api_key": "",
                "openai_api_base": ""
            },
            "project_name": "kedro-test"
        },
        mode="openai"
    )

    client = dataset.load()

    # Example chat completion call (OpenAI client wrapped with Opik tracing)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
             "content": "You are a very accurate calculator. Output only the numeric result."},
            {"role": "user", "content": "12 * 8 = "}
        ],
    )

    print("OpenAI mode response:", response)


def run_langchain():
    """Test LangChain mode using OpikTraceDataset."""
    dataset = OpikTraceDataset(
        credentials={
            "api_key": "",
            "workspace": "",
            "project_name": ""
        },
        mode="langchain",
        tags=["kedro", "test"]
    )

    tracer = dataset.load()

    # Example usage with a simple LangChain-style LLM call
    # Here we just simulate a call using the tracer
    prompt = PromptTemplate.from_template("Echo this input: {text}")
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key="",
        openai_api_base=""
    )

    chain = prompt | llm

    result = chain.invoke({"text": "Hello Opik tracing!"}, config={"callbacks": [tracer]})

    print("LangChain Output:", result.content)


def main():
    run_sdk()
    run_openai()
    run_langchain()


if __name__ == "__main__":
    main()
