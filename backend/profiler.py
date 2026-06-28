"""Profiler — computes dataset statistics and quality metrics."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from backend.dataset_manager import dataset_manager
from backend.models import DatasetProfile

logger = logging.getLogger(__name__)


class Profiler:
    """Computes comprehensive statistics for tabular datasets."""

    def profile(self, dataframe: pd.DataFrame, file_path: str = "") -> DatasetProfile:
        """Build a full profile from an in-memory DataFrame."""
        rows = len(dataframe)
        columns = len(dataframe.columns)
        column_names = list(dataframe.columns)

        dtypes = {col: str(dtype) for col, dtype in dataframe.dtypes.items()}
        missing_values = dataframe.isnull().sum().to_dict()
        missing_values_pct = {
            col: round((count / rows) * 100, 2) if rows else 0.0
            for col, count in missing_values.items()
        }
        duplicate_rows = int(dataframe.duplicated().sum())
        numeric_summary = self._numeric_summary(dataframe)
        preview = dataframe.head(5).replace({pd.NA: None}).to_dict(orient="records")

        profile = DatasetProfile(
            file_path=file_path,
            rows=rows,
            columns=columns,
            column_names=column_names,
            dtypes=dtypes,
            missing_values=missing_values,
            missing_values_pct=missing_values_pct,
            duplicate_rows=duplicate_rows,
            numeric_summary=numeric_summary,
            preview=preview,
        )

        logger.info(
            "[Profiling] Completed | path=%s rows=%d columns=%d duplicates=%d",
            file_path or "in-memory",
            rows,
            columns,
            duplicate_rows,
        )
        return profile

    def profile_file(self, file_path: str, execution_id: str | None = None) -> DatasetProfile:
        """Load and profile a dataset by path."""
        logger.info("[Profiling] Starting profile for %s (execution: %s)", file_path, execution_id)
        dataframe = dataset_manager.load(file_path, execution_id=execution_id)
        resolved = str(dataset_manager.resolve_path(file_path))
        return self.profile(dataframe, file_path=resolved)

    @staticmethod
    def _numeric_summary(dataframe: pd.DataFrame) -> dict[str, dict[str, Any]]:
        """Return describe()-style statistics for numeric columns."""
        numeric_frame = dataframe.select_dtypes(include="number")
        if numeric_frame.empty:
            return {}

        described = numeric_frame.describe().round(4)
        summary: dict[str, dict[str, Any]] = {}

        for column in described.columns:
            summary[column] = {
                stat: Profiler._to_json_safe(described.loc[stat, column])
                for stat in described.index
            }

        return summary

    @staticmethod
    def _to_json_safe(value: Any) -> Any:
        """Convert numpy/pandas scalars to native Python types."""
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            return value.item()
        return value


profiler = Profiler()
