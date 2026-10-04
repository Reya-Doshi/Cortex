"""Tests for DAG topological sorting, dependency scheduling, cycle rejection, and execution state isolation."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

import pandas as pd
import pytest

from backend.dataset_manager import dataset_manager
from backend.executor import executor
from backend.models import ExecutionPlan, ToolStep


@pytest.fixture
def temp_csv_factory(tmp_path: Path):
    """Fixture to create temporary CSV files."""
    def _create_csv(filename: str, data: dict) -> str:
        filepath = tmp_path / filename
        pd.DataFrame(data).to_csv(filepath, index=False)
        return str(filepath)

    return _create_csv


# ---------------------------------------------------------------------------
# 1. DAG Cycle Rejection & Topological Sorting
# ---------------------------------------------------------------------------


def test_topological_sort_rejects_circular_dependency():
    """Verify that _topological_sort raises ValueError when a cycle exists (step1 -> step2 -> step1)."""
    steps = [
        ToolStep(
            id="step1",
            tool="profile",
            dependencies=["step2"],
            description="Step 1 depends on step 2",
            why="Testing cycle",
        ),
        ToolStep(
            id="step2",
            tool="execute_python",
            dependencies=["step1"],
            description="Step 2 depends on step 1",
            why="Testing cycle",
        ),
    ]

    with pytest.raises(ValueError) as exc_info:
        executor._topological_sort(steps)

    assert "Circular dependency detected" in str(exc_info.value)


def test_topological_sort_rejects_nonexistent_dependency():
    """Verify that _topological_sort raises ValueError when a step depends on an unknown ID."""
    steps = [
        ToolStep(
            id="step1",
            tool="profile",
            dependencies=["nonexistent_step_id"],
            description="Step 1 depends on non-existent step",
            why="Testing missing dep",
        ),
    ]

    with pytest.raises(ValueError) as exc_info:
        executor._topological_sort(steps)

    assert "depends on 'nonexistent_step_id' which does not exist" in str(exc_info.value)


def test_executor_handles_cycle_gracefully(temp_csv_factory):
    """Verify that execute() catches circular dependency errors and returns an error result."""
    filepath = temp_csv_factory("data.csv", {"A": [1, 2], "B": [3, 4]})

    plan = ExecutionPlan(
        goal="Cyclic plan test",
        reasoning="Test cyclic error handling",
        confidence=1.0,
        steps=[
            ToolStep(id="a", tool="profile", dependencies=["b"], why="test"),
            ToolStep(id="b", tool="execute_python", dependencies=["a"], why="test"),
        ],
        expected_outputs="None",
    )
    object.__setattr__(plan, "file_path", filepath)

    result = executor.execute(plan, execution_id="test_cycle_exec")
    assert len(result.results) == 1
    assert result.results[0].success is False
    assert "Circular dependency" in result.results[0].error


# ---------------------------------------------------------------------------
# 2. Skipping Dependent Steps on Failure
# ---------------------------------------------------------------------------


def test_executor_skips_steps_when_parent_fails(temp_csv_factory):
    """Verify that if a parent step fails, dependent child steps are skipped."""
    filepath = temp_csv_factory("data.csv", {"A": [1, 2]})

    plan = ExecutionPlan(
        goal="Test failure cascade",
        reasoning="Testing dependency failure skipping",
        confidence=1.0,
        steps=[
            ToolStep(id="failing_step", tool="nonexistent_unknown_tool", dependencies=[], why="Will fail"),
            ToolStep(id="child_step", tool="analyze", dependencies=["failing_step"], why="Should be skipped"),
        ],
        expected_outputs="None",
    )
    object.__setattr__(plan, "file_path", filepath)

    result = executor.execute(plan, execution_id="test_skip_exec")
    
    failing_res = next(r for r in result.results if r.step_id == "failing_step")
    child_res = next(r for r in result.results if r.step_id == "child_step")

    assert failing_res.success is False
    assert child_res.success is False
    assert "Skipped because dependency failed" in child_res.error


# ---------------------------------------------------------------------------
# 3. Concurrent Request State Isolation
# ---------------------------------------------------------------------------


def test_concurrent_request_state_isolation(temp_csv_factory):
    """Verify that two simultaneous execution threads with distinct execution_ids do not bleed DataFrame state."""
    file1 = temp_csv_factory("dataset1.csv", {"department": ["Eng", "Eng"], "salary": [100, 200]})
    file2 = temp_csv_factory("dataset2.csv", {"department": ["Sales", "Sales"], "salary": [50, 50]})

    def worker_run(filepath: str, exec_id: str, expected_dept: str):
        # Load dataset namespaced by execution_id
        df = dataset_manager.load(filepath, execution_id=exec_id)
        # Verify cached key exists with execution_id namespace
        cache_key = f"{exec_id}:{dataset_manager.resolve_path(filepath)}"
        assert cache_key in dataset_manager._cache
        # Check data contents match expected department
        assert list(df["department"])[0] == expected_dept
        return exec_id, cache_key

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as thread_pool:
        f1 = thread_pool.submit(worker_run, file1, "exec_req_1", "Eng")
        f2 = thread_pool.submit(worker_run, file2, "exec_req_2", "Sales")

        res1_id, res1_key = f1.result()
        res2_id, res2_key = f2.result()

    assert res1_key != res2_key
    assert "exec_req_1" in res1_key
    assert "exec_req_2" in res2_key

    # Clean up test keys from manager cache
    dataset_manager.clear_cache()
