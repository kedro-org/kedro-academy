from langfuse._client.datasets import DatasetClient


def test_ds_creation(eval_ds: DatasetClient):
    print(eval_ds)
