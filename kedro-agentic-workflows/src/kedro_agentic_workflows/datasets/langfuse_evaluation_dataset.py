import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from kedro_datasets._typing import JSONPreview
from kedro.io import AbstractDataset, DatasetError
from langfuse import Langfuse
from langfuse.api import Error as LangfuseApiError
from langfuse.api import NotFoundError as LangfuseNotFoundError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from kedro_datasets.json import JSONDataset
    from kedro_datasets.yaml import YAMLDataset
    from langfuse._client.datasets import DatasetClient

SUPPORTED_FILE_EXTENSIONS = {".json", ".yaml", ".yml"}
REQUIRED_LANGFUSE_CREDENTIALS = {"public_key", "secret_key"}
OPTIONAL_LANGFUSE_CREDENTIALS = {"host"}
VALID_SYNC_POLICIES = {"local", "remote"}


class LangfuseEvaluationDataset(AbstractDataset[list[dict[str, Any]], "DatasetClient"]):
    """Kedro dataset for Langfuse evaluation datasets.

    Connects to a Langfuse evaluation dataset and returns a ``DatasetClient``
    on ``load()``, which can be used to run experiments via
    ``dataset.run_experiment()``. Supports an optional local JSON/YAML file
    as the authoring surface for evaluation items.

    **Sync policies:**

    - **local** (default): The local file is the source of truth for evaluation
      items. On ``load()``, the remote dataset is created if it does not exist,
      and any local items missing from the remote (compared by ``id``) are
      uploaded. Existing remote items are never modified or deleted. Items
      without an ``id`` field cannot be deduplicated and will be re-uploaded on
      every load.
    - **remote**: The remote Langfuse dataset is the sole source of truth.
      On ``load()``, the remote dataset is fetched as-is with no local file
      interaction. ``save()`` is a no-op in this mode. An optional ``version``
      (ISO 8601 timestamp) can pin ``load()`` to a historical snapshot.
    """

    def __init__(
        self,
        dataset_name: str,
        credentials: dict[str, str],
        local_path: str | None = None,
        sync_policy: Literal["local", "remote"] = "local",
        metadata: dict[str, Any] | None = None,
        version: str | None = None,
    ):
        self._validate_init_params(credentials, local_path, sync_policy, version)

        self.dataset_name = dataset_name
        self._dataset: DatasetClient | None = None
        self.local_path = Path(local_path) if local_path else None
        self.sync_policy = sync_policy
        self.metadata = metadata
        self._version = self._parse_version(version)
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
        version: str | None,
    ) -> None:
        self._validate_credentials(credentials)
        self._validate_sync_policy(sync_policy)
        self._validate_local_path(local_path)
        if version is not None and sync_policy != "remote":
            raise DatasetError(
                "The 'version' parameter can only be used with "
                "sync_policy='remote'. A versioned load returns a historical "
                "snapshot which is incompatible with local-to-remote sync."
            )

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

    @staticmethod
    def _parse_version(version: str | None) -> datetime | None:
        """Parse an ISO 8601 version string into a timezone-aware UTC datetime."""
        if version is None:
            return None
        try:
            dt = datetime.fromisoformat(version)
        except (ValueError, TypeError) as exc:
            raise DatasetError(
                f"Invalid version '{version}'. "
                f"Expected ISO 8601 format (e.g. '2026-01-15T00:00:00Z')."
            ) from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    @property
    def file_dataset(self) -> "JSONDataset | YAMLDataset":
        """Return JSON/YAML file dataset based on extension."""
        if not self.local_path:
            raise DatasetError("local_path must be provided for file dataset operations.")
        if self._file_dataset is None:
            if self.local_path.suffix.lower() in (".yaml", ".yml"):
                from kedro_datasets.yaml import YAMLDataset
                self._file_dataset = YAMLDataset(filepath=str(self.local_path))
            else:
                from kedro_datasets.json import JSONDataset
                self._file_dataset = JSONDataset(filepath=str(self.local_path))
        return self._file_dataset

    def _get_or_create_remote_dataset(self) -> "DatasetClient":
        """Ensure the remote Langfuse dataset exists, creating it if not found.

        Returns the latest ``DatasetClient``.
        """
        try:
            return self._client.get_dataset(name=self.dataset_name)
        except LangfuseNotFoundError:
            pass
        except LangfuseApiError as exc:
            raise DatasetError(
                f"Langfuse API error while fetching dataset '{self.dataset_name}': {exc}"
            ) from exc

        try:
            logger.info(
                "Dataset '%s' not found on Langfuse, creating it.",
                self.dataset_name,
            )
            self._client.create_dataset(
                name=self.dataset_name,
                metadata=self.metadata or {},
            )
            return self._client.get_dataset(name=self.dataset_name)
        except LangfuseApiError as exc:
            raise DatasetError(
                f"Langfuse API error while creating dataset '{self.dataset_name}': {exc}"
            ) from exc

    def _validate_items(self, items: list[dict[str, Any]]) -> None:
        """Validate that all items contain the required 'input' key."""
        for i, item in enumerate(items):
            if "input" not in item:
                raise DatasetError(
                    f"Dataset item at index {i} is missing required 'input' key."
                )

    @staticmethod
    def _merge_items(
        existing: list[dict[str, Any]],
        new: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge new items into existing list, deduplicating by 'id'.

        Items without an 'id' key are always appended.
        For items with an 'id', existing items take precedence (new duplicates
        are dropped).
        """
        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []

        for item in existing:
            item_id = item.get("id")
            if item_id is not None:
                seen_ids.add(item_id)
            merged.append(item)

        for item in new:
            item_id = item.get("id")
            if item_id is not None and item_id in seen_ids:
                continue
            if item_id is not None:
                seen_ids.add(item_id)
            merged.append(item)

        return merged

    def _upload_items(self, items: list[dict[str, Any]]) -> None:
        """Upload items to the remote Langfuse dataset.

        Callers are responsible for validating items before calling this method.
        """
        for item in items:
            self._client.create_dataset_item(
                dataset_name=self.dataset_name,
                id=item.get("id"),
                input=item["input"],
                expected_output=item.get("expected_output"),
                metadata=item.get("metadata"),
            )

    def _filter_new_items(
        self,
        items: list[dict[str, Any]],
        dataset: "DatasetClient",
    ) -> list[dict[str, Any]]:
        """Return items not already present on remote, compared by 'id'.

        Items without an 'id' key are always included (cannot be deduplicated).
        """
        items_with_id = [item for item in items if "id" in item]
        items_without_id = [item for item in items if "id" not in item]

        if items_without_id:
            logger.warning(
                "Found %d item(s) without an 'id' field. "
                "Items without 'id' cannot be deduplicated and will be "
                "uploaded every time. Consider adding unique 'id' fields.",
                len(items_without_id),
            )

        remote_ids = {item.id for item in dataset.items}
        missing_items = [
            item for item in items_with_id
            if item["id"] not in remote_ids
        ]

        return missing_items + items_without_id

    def _sync_local_to_remote(self, dataset: "DatasetClient") -> "DatasetClient":
        """Sync local items to remote, uploading only items missing from remote.

        Compares local items against remote items by 'id'. Items present in the
        local file but absent from the remote dataset are uploaded. Existing
        remote items are never modified or deleted.

        Returns the (possibly refreshed) DatasetClient.
        """
        if not self.local_path or not self.local_path.exists():
            return dataset

        local_items = self.file_dataset.load()
        self._validate_items(local_items)

        new_items = self._filter_new_items(local_items, dataset)
        if not new_items:
            return dataset

        logger.info(
            "Syncing %d new item(s) from '%s' to remote dataset '%s'.",
            len(new_items),
            self.local_path,
            self.dataset_name,
        )
        self._upload_items(new_items)
        return self._client.get_dataset(name=self.dataset_name)

    def load(self) -> "DatasetClient":
        """Load the Langfuse evaluation dataset.

        Creates the remote dataset if it does not exist. When
        ``sync_policy="local"``, any local items missing from the remote
        (compared by ``id``) are uploaded before returning. When ``version``
        is set (remote mode only), returns items as they existed at that
        point in time.

        Returns:
            ``DatasetClient`` that can be used to iterate items or call
            ``run_experiment()``.
        """
        dataset = self._get_or_create_remote_dataset()

        if self._version is not None:
            logger.info(
                "Loading versioned snapshot of '%s' at %s.",
                self.dataset_name,
                self._version.isoformat(),
            )
            dataset = self._client.get_dataset(
                name=self.dataset_name, version=self._version
            )

        if self.sync_policy == "local":
            dataset = self._sync_local_to_remote(dataset)

        logger.info(
            "Loaded dataset '%s' with %d item(s) (sync_policy='%s').",
            self.dataset_name,
            len(dataset.items),
            self.sync_policy,
        )
        self._dataset = dataset
        return dataset

    def save(self, data: list[dict[str, Any]]) -> None:
        """Save evaluation items to remote and optionally to local file.

        Items already present on remote (matched by ``id``) are skipped.
        When ``local_path`` is set, items are also merged into the local
        file with the same id-based deduplication. No-op when
        ``sync_policy="remote"``.
        """
        if self.sync_policy == "remote":
            logger.warning(
                "save() is a no-op when sync_policy='remote' for dataset '%s'. "
                "Remote datasets are managed externally.",
                self.dataset_name,
            )
            return

        dataset = self._get_or_create_remote_dataset()
        self._validate_items(data)
        new_items = self._filter_new_items(data, dataset)
        if new_items:
            logger.info(
                "Uploading %d new item(s) to remote dataset '%s'.",
                len(new_items),
                self.dataset_name,
            )
            self._upload_items(new_items)
        else:
            logger.info(
                "No new items to upload to remote dataset '%s'.",
                self.dataset_name,
            )

        if self.local_path:
            existing = []
            if self.local_path.exists():
                existing = self.file_dataset.load()
            merged = self._merge_items(existing, data)
            self.file_dataset.save(merged)

    def _exists(self) -> bool:
        try:
            self._client.get_dataset(name=self.dataset_name)
            return True
        except LangfuseNotFoundError:
            return False
        except LangfuseApiError as exc:
            raise DatasetError(
                f"Langfuse API error while checking dataset '{self.dataset_name}': {exc}"
            ) from exc

    def _describe(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "local_path": str(self.local_path) if self.local_path else None,
            "sync_policy": self.sync_policy,
            "version": self._version.isoformat() if self._version else None,
            "metadata": self.metadata,
        }

    def preview(self) -> JSONPreview:
        """Generate a JSON-compatible preview of the local evaluation data for Kedro-Viz."""
        if not self.local_path:
            return JSONPreview("No local_path configured.")

        if not self.local_path.exists():
            return JSONPreview("Local file does not exist.")

        local_data = self.file_dataset.load()

        if isinstance(local_data, str):
            local_data = {"content": local_data}

        return JSONPreview(json.dumps(local_data))
