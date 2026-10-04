"""Behavioral and edge-case unit tests for dataset loading, profiling, and planning."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from backend.dataset_manager import dataset_manager
from backend.models import ExecutionPlan
from backend.planner import planner, validate_intent_columns
from backend.profiler import profiler
from backend.tools import tool_execute_python, tool_visualize


@pytest.fixture
def temp_csv_factory(tmp_path: Path):
    """Fixture to create temporary CSV files."""
    def _create_csv(filename: str, data: dict | str) -> str:
        filepath = tmp_path / filename
        if isinstance(data, str):
            filepath.write_text(data, encoding="utf-8")
        else:
            pd.DataFrame(data).to_csv(filepath, index=False)
        return str(filepath)

    return _create_csv


# ---------------------------------------------------------------------------
# 1. Empty and Malformed CSV Validation
# ---------------------------------------------------------------------------


def test_empty_csv_file_raises_value_error(temp_csv_factory):
    """Verify that an empty CSV file raises a clear ValueError."""
    filepath = temp_csv_factory("empty.csv", "")
    with pytest.raises(ValueError) as exc_info:
        dataset_manager.load(filepath, use_cache=False)
    assert "empty" in str(exc_info.value).lower()


def test_no_rows_csv_raises_value_error(temp_csv_factory):
    """Verify that a CSV with headers but zero data rows raises ValueError."""
    filepath = temp_csv_factory("headers_only.csv", "col1,col2\n")
    with pytest.raises(ValueError) as exc_info:
        dataset_manager.load(filepath, use_cache=False)
    assert "no rows" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()


def test_invalid_extension_raises_value_error():
    """Verify that non-CSV file extensions are rejected."""
    with pytest.raises(ValueError) as exc_info:
        dataset_manager.validate_csv_extension("dataset.json")
    assert "Invalid file type" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. Null Values & Missing Data Profiling
# ---------------------------------------------------------------------------


def test_profiler_handles_null_values_correctly(temp_csv_factory):
    """Verify that missing values and missing value percentages are correctly computed."""
    filepath = temp_csv_factory(
        "nulls.csv",
        {
            "name": ["Alice", "Bob", None, "Dave"],
            "age": [25.0, None, 30.0, None],
            "salary": [50000, 60000, 70000, 80000],
        },
    )

    prof = profiler.profile_file(filepath, execution_id="test_nulls")
    assert prof.rows == 4
    assert prof.columns == 3
    assert prof.missing_values["age"] == 2
    assert prof.missing_values_pct["age"] == 50.0
    assert prof.missing_values["name"] == 1
    assert prof.missing_values_pct["name"] == 25.0
    assert prof.missing_values["salary"] == 0


# ---------------------------------------------------------------------------
# 3. Intent Column Validation Safeguards
# ---------------------------------------------------------------------------


def test_validate_intent_columns_detects_missing_age():
    """Verify that missing required columns for age survival analysis raise ValueError."""
    cols = ["PassengerId", "Survived", "Name"]
    with pytest.raises(ValueError) as exc_info:
        validate_intent_columns("Which age group survived the most?", cols)
    assert "Required columns" in str(exc_info.value)
    assert "Age" in str(exc_info.value)


def test_validate_intent_columns_passes_when_present():
    """Verify that validate_intent_columns passes when all required semantic columns exist."""
    cols = ["PassengerId", "Age", "Survived", "Sex"]
    # Should not raise any exception
    validate_intent_columns("Which age group survived the most?", cols)
    validate_intent_columns("What is survival by sex?", cols)


# ---------------------------------------------------------------------------
# 4. Tool Execution Fallbacks & Unsupported Operations
# ---------------------------------------------------------------------------


def test_tool_execute_python_unsupported_operation_fallback(temp_csv_factory):
    """Verify that an unknown operation string falls back gracefully without crashing."""
    filepath = temp_csv_factory(
        "dept.csv",
        {
            "department": ["Engineering", "HR", "Marketing"],
            "salary": [100000, 60000, 75000],
        },
    )

    result = tool_execute_python(
        file_path=filepath,
        execution_id="test_unsupported_op",
        operation="unknown_nonexistent_operation",
    )

    assert result["status"] == "success"
    assert "data" in result
    assert len(result["data"]) > 0


def test_tool_visualize_handles_empty_or_missing_dependency():
    """Verify visualizer handles missing dependency outputs with fallback visual spec."""
    result = tool_visualize(dependency_outputs=None, chart_type="line")
    assert result["status"] == "success"
    assert result["chart_type"] == "line"
    assert "data" in result
    assert len(result["data"]) > 0


# ---------------------------------------------------------------------------
# 5. Malformed Planner Output Fallback Path
# ---------------------------------------------------------------------------


def test_planner_fallback_on_malformed_llm_response(temp_csv_factory):
    """Verify that when Gemini LLM raises an exception or returns empty output, Planner returns a valid fallback plan."""
    filepath = temp_csv_factory("data.csv", {"A": [1, 2], "B": [3, 4]})

    with patch("backend.planner.client.models.generate_content", side_effect=Exception("API Timeout / Outage")):
        plan = planner.create_plan("Summarize dataset", [filepath], execution_id="test_fallback")

    assert isinstance(plan, ExecutionPlan)
    assert plan.confidence == 0.5
    assert len(plan.steps) >= 2
    assert plan.steps[0].tool == "profile"
    assert plan.steps[-1].tool == "analyze"
