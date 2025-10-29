from kedro_agentic_workflows.datasets.langfuse_trace_dataset import LangfuseTraceDataset


def run_openai():
    # With custom host
    dataset = LangfuseTraceDataset(
        credentials={
            "public_key": "",
            "secret_key": "",
            "host": "https://cloud.langfuse.com",
            "openai": {"openai_api_base": "", "openai_api_key": ""}
        },
        mode="openai"
    )

    # Load tracing client
    client = dataset.load()
    response = client.chat.completions.create(
        name="test-chat",
        model="gpt-4o",
        messages=[
            {"role": "system",
             "content": "You are a very accurate calculator. You output only the result of the calculation."},
            {"role": "user", "content": "1 + 1 = "}],
        metadata={"someMetadataKey": "someValue"},
    )

    print(response)


def run_sdk():
    # With custom host
    dataset = LangfuseTraceDataset(
        credentials={
            "public_key": "",
            "secret_key": "",
            "host": "https://cloud.langfuse.com",
        },
        mode="sdk"
    )

    from langfuse import observe

    # Load tracing client
    langfuse = dataset.load()

    @observe
    def my_function():
        return "Hello, world!"  # Input/output and timings are automatically captured

    my_function()


if __name__ == "__main__":
    run_openai()
    run_sdk()
