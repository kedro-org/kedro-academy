import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Union

from kedro.io import AbstractDataset, DatasetError
from kedro_datasets._typing import JSONPreview
from opik import Opik
from opik.api_objects.dataset.dataset import Dataset
from opik.rest_api.core.api_error import ApiError

if TYPE_CHECKING:
    from kedro_datasets.json import JSONDataset
    from kedro_datasets.yaml import YAMLDataset

SUPPORTED_FILE_EXTENSIONS = [".json", ".yaml", ".yml"]


class OpikEvaluationDataset(AbstractDataset):
    """Kedro dataset for Opik evaluation datasets supporting local->remote sync (local mode)
    and remote-only behavior (remote mode).
    """

    def __init__(
        self,
        dataset_name: str,
        credentials: dict[str, str],
        local_path: Optional[str] = None,
        sync_policy: str = "local",
    ):
        self.dataset_name = dataset_name
        self.local_path = Path(local_path) if local_path else None
        self.sync_policy = sync_policy
        self._file_dataset = None

        try:
            self._client = Opik(**credentials)
        except Exception as e:
            raise DatasetError(f"Failed to initialise Opik client: {e}")

    @property
    def file_dataset(self) -> Union["JSONDataset", "YAMLDataset"]:
        """Return a JSON or YAML file dataset based on the local_path extension."""
        if not self.local_path:
            raise RuntimeError("local_path must be provided for file dataset operations.")
        if self._file_dataset is None:
            suffix = self.local_path.suffix.lower()
            if suffix in [".yaml", ".yml"]:
                from kedro_datasets.yaml import YAMLDataset  # noqa: PLC0415
                self._file_dataset = YAMLDataset(filepath=str(self.local_path))
            elif suffix == ".json":
                from kedro_datasets.json import JSONDataset  # noqa: PLC0415
                self._file_dataset = JSONDataset(filepath=str(self.local_path))
            else:
                raise NotImplementedError(
                    f"Unsupported file extension '{self.local_path.suffix}'. "
                    f"Supported formats: {', '.join(sorted(SUPPORTED_FILE_EXTENSIONS))}"
                )
        return self._file_dataset

    def load(self) -> Dataset:
        """Return the Opik Dataset object, creating and seeding it if it does not exist.

        When sync_policy="local" and the dataset is created for the first time,
        items from the local file are inserted automatically.

        Returns:
            opik.Dataset: The Opik dataset ready for use in experiments.

        Raises:
            DatasetError: If the Opik API returns an unexpected error.
        """
        try:
            dataset = self._client.get_dataset(name=self.dataset_name)
        except ApiError as e:
            if e.status_code != 404:
                raise DatasetError(
                    f"Failed to fetch Opik dataset '{self.dataset_name}': {e}"
                )

            dataset = self._client.create_dataset(
                name=self.dataset_name,
                description=f"Created by Kedro (sync_policy={self.sync_policy})",
            )

            if (
                self.sync_policy == "local"
                and self.local_path
                and self.local_path.exists()
            ):
                local_items = self.file_dataset.load()

                for item in local_items:
                    if "input" not in item:
                        raise ValueError("Each dataset item must contain 'input'.")

                # Opik requires item IDs to be valid UUIDs; strip non-UUID IDs
                # so the SDK generates them automatically. Deduplication is
                # content-hash-based and unaffected by the ID field.
                items_to_insert = [
                    {k: v for k, v in item.items() if k != "id"}
                    for item in local_items
                ]
                dataset.insert(items_to_insert)

            # Reload so the dataset's internal hash state reflects inserted items
            dataset = self._client.get_dataset(name=self.dataset_name)

        return dataset

    def save(self, data: List[dict[str, Any]]) -> None:
        """Insert items into the Opik dataset and optionally update the local file.

        In remote sync policy, this is a no-op.

        Args:
            data: List of dicts, each containing at least an ``input`` key.

        Raises:
            DatasetError: If the Opik API call fails.
            ValueError: If any item is missing the required ``input`` key.
        """
        if self.sync_policy == "remote":
            return

        for item in data:
            if "input" not in item:
                raise ValueError("Each dataset item must contain 'input'.")

        try:
            opik_dataset = self._client.get_or_create_dataset(name=self.dataset_name)
        except Exception as e:
            raise DatasetError(f"Failed to get or create Opik dataset: {e}")

        opik_dataset.insert(data)

        if self.sync_policy == "local" and self.local_path:
            existing: List[dict] = []
            if self.local_path.exists():
                existing = self.file_dataset.load()
            self.file_dataset.save(existing + data)

    def _exists(self) -> bool:
        try:
            self._client.get_dataset(name=self.dataset_name)
            return True
        except ApiError as e:
            if e.status_code == 404:
                return False
            raise

    def _describe(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "local_path": str(self.local_path) if self.local_path else None,
            "sync_policy": self.sync_policy,
        }

    def preview(self) -> JSONPreview:
        """
        Generate a JSON-compatible preview of the underlying prompt data for Kedro-Viz.

        Automatically wraps string content in a JSON object to ensure compatibility
        with Kedro-Viz's JSON preview requirements. This prevents "src property must
        be a valid json object" errors when the local file contains plain text.

        Returns:
            JSONPreview: A Kedro-Viz-compatible object containing a serialized JSON string.
                String content is wrapped in {"content": <string>} format for proper
                JSON object structure. Returns error message if local file doesn't exist.
        """
        if self.local_path and self.local_path.exists():
            local_data = self.file_dataset.load()

            if isinstance(local_data, str):
                local_data = {"content": local_data}

            return JSONPreview(json.dumps(local_data))
        
        return JSONPreview("Local evaluation dataset does not exist.")
