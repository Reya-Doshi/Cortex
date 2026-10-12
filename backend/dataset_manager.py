"""Dataset Manager — uploads, path resolution, loading, and caching."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from backend.config import DATASETS_DIR, MAX_UPLOAD_BYTES, PROJECT_ROOT, UPLOADS_DIR

logger = logging.getLogger(__name__)

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class DatasetManager:
    """Handles dataset file I/O and in-memory DataFrame caching."""

    def __init__(self) -> None:
        self._cache: dict[str, pd.DataFrame] = {}

    @staticmethod
    def get_project_root() -> Path:
        """Return the Cortex project root directory."""
        return PROJECT_ROOT

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Return a filesystem-safe version of an uploaded filename."""
        name = Path(filename).name.strip()
        if not name:
            raise ValueError("Filename cannot be empty.")

        stem = Path(name).stem
        suffix = Path(name).suffix.lower()
        safe_stem = _UNSAFE_FILENAME_CHARS.sub("_", stem).strip("._") or "dataset"
        return f"{safe_stem}{suffix}"

    @staticmethod
    def validate_csv_extension(filename: str) -> None:
        """Raise ValueError if the filename is not a CSV."""
        suffix = Path(filename).suffix.lower()
        if suffix != ".csv":
            raise ValueError(f"Invalid file type '{suffix}'. Only .csv files are supported.")

    def resolve_path(self, file_path: str) -> Path:
        """Resolve a dataset path from uploads, datasets, or project root."""
        candidate = Path(file_path)

        if candidate.is_absolute():
            if candidate.exists():
                resolved = candidate.resolve()
                logger.debug("[Upload] Resolved absolute path: %s", resolved)
                return resolved
            raise FileNotFoundError(f"Absolute path provided but file does not exist: {candidate}")

        candidates = [
            PROJECT_ROOT / file_path,
            UPLOADS_DIR / candidate.name,
            DATASETS_DIR / file_path,
            DATASETS_DIR / candidate.name,
            Path.cwd() / file_path,
        ]

        for path in candidates:
            if path.exists():
                resolved = path.resolve()
                logger.debug("[Upload] Resolved dataset path: %s", resolved)
                return resolved

        checked = "\n".join(str(path) for path in candidates)
        raise FileNotFoundError(f"Dataset file '{file_path}' not found. Checked:\n{checked}")

    def load(self, file_path: str | Path, *, execution_id: str | None = None, use_cache: bool = True, **pd_kwargs: Any) -> pd.DataFrame:
        """Load a CSV dataset, optionally returning a cached DataFrame."""
        path = self.resolve_path(str(file_path))
        
        if execution_id:
            cache_key = f"{execution_id}:{path}"
        else:
            cache_key = str(path)

        if use_cache and cache_key in self._cache:
            logger.debug("[Upload] Cache hit for %s", cache_key)
            return self._cache[cache_key]

        read_kwargs: dict[str, Any] = {"encoding": "utf-8"}
        read_kwargs.update(pd_kwargs)

        try:
            dataframe = pd.read_csv(path, **read_kwargs)
        except UnicodeDecodeError:
            logger.warning("[Upload] UTF-8 decode failed for %s; retrying with latin-1.", path)
            read_kwargs["encoding"] = "latin-1"
            dataframe = pd.read_csv(path, **read_kwargs)
        except pd.errors.EmptyDataError as exc:
            raise ValueError("CSV file is empty.") from exc
        except pd.errors.ParserError as exc:
            raise ValueError(f"CSV parsing failed: {exc}") from exc

        if dataframe.empty:
            raise ValueError("CSV file contains no rows.")

        if use_cache:
            self._cache[cache_key] = dataframe
            logger.info("[Upload] Cached dataset: %s (%d rows)", cache_key, len(dataframe))

        return dataframe

    def invalidate_cache(self, file_path: str | Path) -> None:
        """Remove a dataset from the in-memory cache."""
        cache_key = str(self.resolve_path(str(file_path)))
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.info("[Upload] Invalidated cache for %s", cache_key)

    def clear_cache(self) -> None:
        """Clear all cached DataFrames."""
        self._cache.clear()
        logger.info("[Upload] Cleared dataset cache.")

    def validate_file(self, path: Path) -> dict[str, Any]:
        """Validate a CSV file on disk and return basic metadata."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        self.validate_csv_extension(path.name)
        dataframe = self.load(path, use_cache=False)

        return {
            "rows": len(dataframe),
            "columns": len(dataframe.columns),
            "column_names": list(dataframe.columns),
        }

    def save_upload(self, content: bytes, original_filename: str) -> dict[str, Any]:
        """Validate, persist, and register an uploaded CSV file."""
        if not content:
            raise ValueError("Uploaded file is empty.")

        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError(
                f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            )

        self.validate_csv_extension(original_filename)

        file_id = uuid.uuid4().hex
        safe_name = Path(original_filename).name.replace(" ", "_")
        stored_name = f"{file_id}_{safe_name}"
        destination = UPLOADS_DIR / stored_name

        logger.info("[Upload] Saving uploaded file: %s", destination)
        destination.write_bytes(content)

        try:
            metadata = self.validate_file(destination)
        except ValueError:
            destination.unlink(missing_ok=True)
            raise

        relative_path = destination.relative_to(PROJECT_ROOT).as_posix()
        self.load(destination)

        logger.info(
            "[Upload] Upload complete | file_id=%s rows=%d columns=%d",
            file_id,
            metadata["rows"],
            metadata["columns"],
        )

        return {
            "file_id": file_id,
            "filename": safe_name,
            "file_path": relative_path,
            **metadata,
        }


dataset_manager = DatasetManager()
