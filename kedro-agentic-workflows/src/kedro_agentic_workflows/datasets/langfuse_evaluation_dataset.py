from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Union
from kedro.io import AbstractDataset
from langfuse import Langfuse
from langfuse._client.datasets import DatasetClient
if TYPE_CHECKING:
    from kedro_datasets.json import JSONDataset
    from kedro_datasets.yaml import YAMLDataset

SUPPORTED_FILE_EXTENSIONS = [".json", ".yaml", ".yml"]


class LangfuseEvaluationDataset(AbstractDataset):
    """Kedro dataset for Langfuse evaluations supporting local->remote sync (local mode)
       and remote-only behavior (remote mode)."""

    def __init__(
        self,
        dataset_name: str,
        credentials: dict[str, str],
        local_path: Optional[str] = None,
        sync_policy: str = "local",  # "local" | "remote"
    ):
        self.dataset_name = dataset_name
        self.local_path = Path(local_path) if local_path else None
        self.sync_policy = sync_policy
        self._client = Langfuse(
            public_key=credentials["public_key"],
            secret_key=credentials["secret_key"],
            host=credentials.get("host"),
        )
        self._file_dataset = None

    @property
    def file_dataset(self) -> Union["JSONDataset", "YAMLDataset"]:
        """Return JSON/YAML file dataset based on extension."""
        if not self.local_path:
            raise RuntimeError("local_path must be provided for file dataset operations.")
        if self._file_dataset is None:
            if self.local_path.suffix.lower() in [".yaml", ".yml"]:
                from kedro_datasets.yaml import YAMLDataset
                self._file_dataset = YAMLDataset(filepath=str(self.local_path))
            elif self.local_path.suffix.lower() == ".json":
                from kedro_datasets.json import JSONDataset
                self._file_dataset = JSONDataset(filepath=str(self.local_path))
            else:
                raise NotImplementedError(
                    f"Unsupported file extension '{self.local_path.suffix}'. "
                    f"Supported formats: {', '.join(sorted(SUPPORTED_FILE_EXTENSIONS))}"
                )
        return self._file_dataset

    def load(self) -> DatasetClient:
        """Return remote Langfuse dataset; optionally sync local items to remote."""
        try:
            dataset = self._client.get_dataset(name=self.dataset_name)
        except Exception:
            # Create remote dataset if not exist
            dataset = self._client.create_dataset(name=self.dataset_name)

        # Local -> remote sync (only append)
        if self.sync_policy == "local" and self.local_path and self.local_path.exists():
            local_items = self.file_dataset.load()
            for item in local_items:
                # Use core client to create dataset item in remote
                self._client.create_dataset_item(
                    dataset_name=self.dataset_name,
                    input=item.get("input"),
                    expected_output=item.get("expected_output"),
                    metadata=item.get("metadata"),
                )

        # In remote mode, do *not* read remote items back into local file

        return dataset

    def save(self, data: List[dict[str, Any]]) -> None:
        """Append new items to remote dataset and optionally update local file."""
        _ = self.load()
        for item in data:
            self._client.create_dataset_item(
                dataset_name=self.dataset_name,
                input=item.get("input"),
                expected_output=item.get("expected_output"),
                metadata=item.get("metadata"),
            )

        if self.sync_policy == "local" and self.local_path:
            # Save local file
            self.file_dataset.save(data)

    def _exists(self) -> bool:
        try:
            self._client.get_dataset(name=self.dataset_name)
            return True
        except Exception:
            return False

    def _describe(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "local_path": str(self.local_path) if self.local_path else None,
            "sync_policy": self.sync_policy,
        }
