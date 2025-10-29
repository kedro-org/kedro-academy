import os
import time

from opik import configure, track, opik_context
from opik.integrations.openai import track_openai
from opik.integrations.langchain import OpikTracer

import openai
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


def set_credentials(api_key: str, workspace: str, openai_key: str, base_url: str):
    """Set environment variables for Opik and OpenAI."""
    os.environ["OPIK_API_KEY"] = api_key
    os.environ["OPIK_WORKSPACE"] = workspace
    os.environ["OPIK_PROJECT_NAME"] = "test-clients"
    os.environ["OPENAI_API_KEY"] = openai_key
    os.environ["OPENAI_API_BASE"] = base_url

    # Optional arguments
    # OPIK_URL_OVERRIDE = "https://www.comet.com/opik/api"
    # OPIK_PROJECT_NAME = "your-project-name"


def reset_credentials():
    """Remove environment variables (optional cleanup)."""
    for env in ["OPIK_API_KEY", "OPIK_WORKSPACE", "OPENAI_API_KEY"]:
        os.environ.pop(env, None)


def run_sdk():
    """
    Demonstrate using the Opik Python SDK directly.
    Use the @track decorator to trace a sample function, flush, etc.
    """
    # configure opik (reads from env by default)
    configure()

    @track(name="my_sample_workflow")
    def my_workflow(x: int, y: int) -> int:
        # simulate some work
        time.sleep(0.1)
        return x + y

    # call the function so a trace is recorded
    result = my_workflow(3, 4)
    print("Result from my_workflow:", result)


def run_openai():
    """
    Demonstrate wrapping OpenAI client to produce Opik traces via the OpenAI integration.
    """
    configure()

    # create the OpenAI client and wrap with tracing
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE"))
    tracked = track_openai(client)

    resp = tracked.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say hello"}]
    )
    print("OpenAI response:", resp.choices[0].message.content)


def run_langchain():
    """Demonstrate LangChain + Opik tracing (modern LCEL style, no LLMChain)."""
    configure()

    tracer = OpikTracer()

    prompt = PromptTemplate.from_template("Echo this input: {text}")
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_API_BASE")
    )

    chain = prompt | llm

    result = chain.invoke({"text": "Hello Opik tracing!"}, config={"callbacks": [tracer]})

    print("LangChain Output:", result.content)

    try:
        tracer.flush()
    except Exception:
        pass


def main():
    OPIK_API_KEY = ""
    OPIK_WORKSPACE = ""
    OPENAI_KEY = ""
    OPENAI_BASE_URL = ""

    set_credentials(OPIK_API_KEY, OPIK_WORKSPACE, OPENAI_KEY, OPENAI_BASE_URL)

    print("=== Running SDK demo ===")
    run_sdk()

    print("\n=== Running OpenAI demo ===")
    run_openai()

    print("\n=== Running LangChain demo ===")
    run_langchain()

    # Optionally, cleanup
    reset_credentials()


if __name__ == "__main__":
    main()
