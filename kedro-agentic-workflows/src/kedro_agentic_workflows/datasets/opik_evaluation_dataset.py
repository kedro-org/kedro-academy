import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from kedro.io import AbstractDataset, DatasetError
from kedro_datasets._typing import JSONPreview
from opik import Opik
from opik.api_objects.dataset.dataset import Dataset
from opik.rest_api.core.api_error import ApiError

if TYPE_CHECKING:
    from kedro_datasets.json import JSONDataset
    from kedro_datasets.yaml import YAMLDataset

logger = logging.getLogger(__name__)

SUPPORTED_FILE_EXTENSIONS = {".json", ".yaml", ".yml"}
REQUIRED_OPIK_CREDENTIALS = {"api_key"}
OPTIONAL_OPIK_CREDENTIALS = {"workspace", "host", "project_name"}
VALID_SYNC_POLICIES = {"local", "remote"}


class OpikEvaluationDataset(AbstractDataset):
    """Kedro dataset for Opik evaluation datasets supporting local->remote sync (local mode)
    and remote-only behavior (remote mode).
    """

    def __init__(
        self,
        dataset_name: str,
        credentials: dict[str, str],
        filepath: str | None = None,
        sync_policy: Literal["local", "remote"] = "local",
        metadata: dict[str, Any] | None = None,
    ):
        self._validate_init_params(credentials, filepath, sync_policy)

        self._dataset_name = dataset_name
        self._filepath = Path(filepath) if filepath else None
        self._sync_policy = sync_policy
        self._metadata = metadata
        self._file_dataset = None

        try:
            self._client = Opik(**credentials)
        except Exception as e:
            raise DatasetError(f"Failed to initialise Opik client: {e}") from e

    @staticmethod
    def _validate_init_params(
        credentials: dict[str, str],
        filepath: str | None,
        sync_policy: str,
    ) -> None:
        OpikEvaluationDataset._validate_credentials(credentials)
        OpikEvaluationDataset._validate_sync_policy(sync_policy)
        OpikEvaluationDataset._validate_filepath(filepath)

    @staticmethod
    def _validate_credentials(credentials: dict[str, str]) -> None:
        for key in REQUIRED_OPIK_CREDENTIALS:
            if key not in credentials:
                raise DatasetError(
                    f"Missing required Opik credential: '{key}'."
                )
            if not credentials[key] or not str(credentials[key]).strip():
                raise DatasetError(
                    f"Opik credential '{key}' cannot be empty."
                )
        for key in OPTIONAL_OPIK_CREDENTIALS:
            if key in credentials and (
                not credentials[key] or not str(credentials[key]).strip()
            ):
                raise DatasetError(
                    f"Opik credential '{key}' cannot be empty if provided."
                )

    @staticmethod
    def _validate_sync_policy(sync_policy: str) -> None:
        if sync_policy not in VALID_SYNC_POLICIES:
            raise DatasetError(
                f"Invalid sync_policy '{sync_policy}'. "
                f"Must be one of: {', '.join(sorted(VALID_SYNC_POLICIES))}."
            )

    @staticmethod
    def _validate_filepath(filepath: str | None) -> None:
        if filepath is None:
            return
        suffix = Path(filepath).suffix.lower()
        if suffix not in SUPPORTED_FILE_EXTENSIONS:
            raise DatasetError(
                f"Unsupported file extension '{suffix}'. "
                f"Supported formats: {', '.join(sorted(SUPPORTED_FILE_EXTENSIONS))}."
            )

    @property
    def file_dataset(self) -> "JSONDataset | YAMLDataset":
        """Return a JSON or YAML file dataset based on the filepath extension."""
        if not self._filepath:
            raise DatasetError("filepath must be provided for file dataset operations.")
        if self._file_dataset is None:
            suffix = self._filepath.suffix.lower()
            if suffix in (".yaml", ".yml"):
                from kedro_datasets.yaml import YAMLDataset  # noqa: PLC0415
                self._file_dataset = YAMLDataset(filepath=str(self._filepath))
            else:
                from kedro_datasets.json import JSONDataset  # noqa: PLC0415
                self._file_dataset = JSONDataset(filepath=str(self._filepath))
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
            dataset = self._client.get_dataset(name=self._dataset_name)
        except ApiError as e:
            if e.status_code != 404:
                raise DatasetError(
                    f"Failed to fetch Opik dataset '{self._dataset_name}': {e}"
                ) from e

            dataset = self._client.create_dataset(
                name=self._dataset_name,
                description=f"Created by Kedro (sync_policy={self._sync_policy})",
            )

            if (
                self._sync_policy == "local"
                and self._filepath
                and self._filepath.exists()
            ):
                local_items = self.file_dataset.load()

                for item in local_items:
                    if "input" not in item:
                        raise DatasetError(
                            "Each dataset item must contain 'input'."
                        )

                # Opik requires item IDs to be valid UUIDs; strip non-UUID IDs
                # so the SDK generates them automatically. Deduplication is
                # content-hash-based and unaffected by the ID field.
                items_to_insert = [
                    {k: v for k, v in item.items() if k != "id"}
                    for item in local_items
                ]
                dataset.insert(items_to_insert)

            # Reload so the dataset's internal hash state reflects inserted items
            dataset = self._client.get_dataset(name=self._dataset_name)

        return dataset

    def save(self, data: list[dict[str, Any]]) -> None:
        """Insert items into the Opik dataset and optionally update the local file.

        In remote sync policy, this is a no-op.

        Args:
            data: List of dicts, each containing at least an ``input`` key.

        Raises:
            DatasetError: If the Opik API call fails or any item is missing ``input``.
        """
        if self._sync_policy == "remote":
            return

        for item in data:
            if "input" not in item:
                raise DatasetError("Each dataset item must contain 'input'.")

        try:
            opik_dataset = self._client.get_or_create_dataset(name=self._dataset_name)
        except Exception as e:
            raise DatasetError(f"Failed to get or create Opik dataset: {e}") from e

        opik_dataset.insert(data)

        if self._sync_policy == "local" and self._filepath:
            existing: list[dict] = []
            if self._filepath.exists():
                existing = self.file_dataset.load()
            self.file_dataset.save(existing + data)

    def _exists(self) -> bool:
        try:
            self._client.get_dataset(name=self._dataset_name)
            return True
        except ApiError as e:
            if e.status_code == 404:
                return False
            raise

    def _describe(self) -> dict[str, Any]:
        return {
            "dataset_name": self._dataset_name,
            "filepath": str(self._filepath) if self._filepath else None,
            "sync_policy": self._sync_policy,
            "metadata": self._metadata,
        }

    def preview(self) -> JSONPreview:
        """Generate a JSON-compatible preview of the local evaluation data for Kedro-Viz.

        Returns:
            JSONPreview: A Kedro-Viz-compatible object containing a serialized JSON string.
                Returns a descriptive message if filepath is not configured or does not exist.
        """
        if not self._filepath:
            return JSONPreview("No filepath configured.")

        if not self._filepath.exists():
            return JSONPreview("Local evaluation dataset does not exist.")

        local_data = self.file_dataset.load()

        if isinstance(local_data, str):
            local_data = {"content": local_data}

        return JSONPreview(json.dumps(local_data))
