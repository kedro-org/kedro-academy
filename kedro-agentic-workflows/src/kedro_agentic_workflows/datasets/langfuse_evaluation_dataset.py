import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Union

from kedro_datasets._typing import JSONPreview
from kedro.io import AbstractDataset, DatasetError
from langfuse import Langfuse
from langfuse._client.datasets import DatasetClient
from langfuse.api.core import ApiError

if TYPE_CHECKING:
    from kedro_datasets.json import JSONDataset
    from kedro_datasets.yaml import YAMLDataset

SUPPORTED_FILE_EXTENSIONS = {".json", ".yaml", ".yml"}
REQUIRED_LANGFUSE_CREDENTIALS = {"public_key", "secret_key"}
OPTIONAL_LANGFUSE_CREDENTIALS = {"host"}
VALID_SYNC_POLICIES = {"local", "remote"}


class LangfuseEvaluationDataset(AbstractDataset[list[dict[str, Any]], DatasetClient]):
    """Kedro dataset for Langfuse evaluations supporting local->remote sync (local mode)
       and remote-only behavior (remote mode)."""

    def __init__(
        self,
        dataset_name: str,
        credentials: dict[str, str],
        local_path: str | None = None,
        sync_policy: Literal["local", "remote"] = "local",
        metadata: dict[str, Any] | None = None,
    ):
        self._validate_init_params(credentials, local_path, sync_policy)

        self.dataset_name = dataset_name
        self._dataset: DatasetClient | None = None
        self.local_path = Path(local_path) if local_path else None
        self.sync_policy = sync_policy
        self.metadata = metadata
        self._client = Langfuse(
            public_key=credentials["public_key"],
            secret_key=credentials["secret_key"],
            host=credentials.get("host"),
        )
        self._file_dataset = None

    def _validate_init_params(
        self,
        credentials: dict[str, str],
        local_path: str | None,
        sync_policy: str,
    ) -> None:
        self._validate_credentials(credentials)
        self._validate_sync_policy(sync_policy)
        self._validate_local_path(local_path)

    def _validate_credentials(self, credentials: dict[str, str]) -> None:
        for key in REQUIRED_LANGFUSE_CREDENTIALS:
            if key not in credentials:
                raise DatasetError(
                    f"Missing required Langfuse credential: '{key}'."
                )
            if not credentials[key] or not str(credentials[key]).strip():
                raise DatasetError(
                    f"Langfuse credential '{key}' cannot be empty."
                )
        for key in OPTIONAL_LANGFUSE_CREDENTIALS:
            if key in credentials and (
                not credentials[key] or not str(credentials[key]).strip()
            ):
                raise DatasetError(
                    f"Langfuse credential '{key}' cannot be empty if provided."
                )

    def _validate_sync_policy(self, sync_policy: str) -> None:
        if sync_policy not in VALID_SYNC_POLICIES:
            raise DatasetError(
                f"Invalid sync_policy '{sync_policy}'. "
                f"Must be one of: {', '.join(sorted(VALID_SYNC_POLICIES))}."
            )

    def _validate_local_path(self, local_path: str | None) -> None:
        if local_path is None:
            return
        suffix = Path(local_path).suffix.lower()
        if suffix not in SUPPORTED_FILE_EXTENSIONS:
            raise DatasetError(
                f"Unsupported file extension '{suffix}'. "
                f"Supported formats: {', '.join(sorted(SUPPORTED_FILE_EXTENSIONS))}."
            )

    @property
    def file_dataset(self) -> Union["JSONDataset", "YAMLDataset"]:
        """Return JSON/YAML file dataset based on extension."""
        if not self.local_path:
            raise DatasetError("local_path must be provided for file dataset operations.")
        if self._file_dataset is None:
            if self.local_path.suffix.lower() in (".yaml", ".yml"):
                from kedro_datasets.yaml import YAMLDataset
                self._file_dataset = YAMLDataset(filepath=str(self.local_path))
            elif self.local_path.suffix.lower() == ".json":
                from kedro_datasets.json import JSONDataset
                self._file_dataset = JSONDataset(filepath=str(self.local_path))
            else:
                raise DatasetError(
                    f"Unsupported file extension '{self.local_path.suffix}'. "
                    f"Supported formats: {', '.join(sorted(SUPPORTED_FILE_EXTENSIONS))}"
                )
        return self._file_dataset

    def _get_or_create_remote_dataset(self) -> None:
        """Ensure the remote Langfuse dataset exists, creating it if not found."""
        try:
            self._client.get_dataset(name=self.dataset_name)
        except ApiError as exc:
            if exc.status_code != 404:
                raise DatasetError(
                    f"Langfuse API error while fetching dataset '{self.dataset_name}': {exc}"
                ) from exc
            self._client.create_dataset(
                name=self.dataset_name,
                metadata={
                    "created_by": "kedro",
                    "sync_policy": self.sync_policy,
                }
            )

    def _validate_items(self, items: list[dict[str, Any]]) -> None:
        """Validate that all items contain the required 'input' key."""
        for i, item in enumerate(items):
            if "input" not in item:
                raise DatasetError(
                    f"Dataset item at index {i} is missing required 'input' key."
                )

    def _upload_items(self, items: list[dict[str, Any]]) -> None:
        """Upload items to the remote Langfuse dataset."""
        self._validate_items(items)
        for item in items:
            self._client.create_dataset_item(
                dataset_name=self.dataset_name,
                input=item["input"],
                expected_output=item.get("expected_output"),
                metadata=item.get("metadata"),
            )

    def load(self) -> DatasetClient:
        """Return remote Langfuse dataset; optionally sync local items to remote."""
        try:
            dataset = self._client.get_dataset(name=self.dataset_name)
        except ApiError as exc:
            if exc.status_code != 404:
                raise DatasetError(
                    f"Langfuse API error while fetching dataset '{self.dataset_name}': {exc}"
                ) from exc

            self._client.create_dataset(
                name=self.dataset_name,
                metadata={
                    "created_by": "kedro",
                    "sync_policy": self.sync_policy,
                }
            )

            if (
                    self.sync_policy == "local"
                    and self.local_path
                    and self.local_path.exists()
            ):
                local_items = self.file_dataset.load()
                self._upload_items(local_items)

            dataset = self._client.get_dataset(name=self.dataset_name)

        self._dataset = dataset
        return dataset

    def save(self, data: list[dict[str, Any]]) -> None:
        if self.sync_policy == "remote":
            return

        self._get_or_create_remote_dataset()
        self._upload_items(data)

        if self.local_path:
            existing = []
            if self.local_path.exists():
                existing = self.file_dataset.load()
            self.file_dataset.save(existing + data)

    def _exists(self) -> bool:
        try:
            self._client.get_dataset(name=self.dataset_name)
            return True
        except ApiError as exc:
            if exc.status_code == 404:
                return False
            raise DatasetError(
                f"Langfuse API error while checking dataset '{self.dataset_name}': {exc}"
            ) from exc

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
        if self.local_path.exists():
            local_data = self.file_dataset.load()

            # If local_data is just a string, wrap it in a JSON object
            if isinstance(local_data, str):
                local_data = {"content": local_data}

            return JSONPreview(json.dumps(local_data))

        return JSONPreview("Local prompt does not exist.")
