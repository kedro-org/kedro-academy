from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any

import fsspec
import pypdf
from kedro.io.core import (
    AbstractVersionedDataset,
    DatasetError,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)

DEFAULT_FS_ARGS: dict[str, Any] = {
    "open_args_save": {"mode": "w"},
    "open_args_load": {"mode": "r"},
}


class PDFDataset(AbstractVersionedDataset):
    def __init__(
        self,
        *,
        filepath: str,
        version: Version | None = None,
        credentials: dict[str, Any] | None = None,
        fs_args: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        _fs_args = deepcopy(fs_args) or {}
        _fs_open_args_load = _fs_args.pop("open_args_load", {})
        _fs_open_args_save = _fs_args.pop("open_args_save", {})
        _credentials = deepcopy(credentials) or {}

        protocol, path = get_protocol_and_path(filepath)
        if protocol == "file":
            _fs_args.setdefault("auto_mkdir", True)

        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **_credentials, **_fs_args)

        self.metadata = metadata

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            exists_function=self._fs.exists,
            glob_function=self._fs.glob,
        )

        # Handle default fs arguments
        self._fs_open_args_load = {
            **DEFAULT_FS_ARGS.get("open_args_load", {}),
            **(_fs_open_args_load or {}),
        }
        self._fs_open_args_save = {
            **DEFAULT_FS_ARGS.get("open_args_save", {}),
            **(_fs_open_args_save or {}),
        }

        
    def _describe(self) -> dict[str, Any]:
        return {
            "filepath": self._filepath,
            "protocol": self._protocol,
            "version": self._version,
        }

    def load(self):
        self.pdf_reader = pypdf.PdfReader(stream=str(self._get_load_path()), strict=False, password=None)
        pages = []
        for page in self.pdf_reader.pages:
            pages.append(page.extract_text())
        return pages

    def save(self, data: list) -> None:
        raise DatasetError("Saving to PDFDataset is not supported.")
        pass

    def _exists(self) -> bool:
        try:
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
        except DatasetError:
            return False

        return self._fs.exists(load_path)

    def _release(self) -> None:
        super()._release()
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate underlying filesystem caches."""
        filepath = get_filepath_str(self._filepath, self._protocol)
        self._fs.invalidate_cache(filepath)
