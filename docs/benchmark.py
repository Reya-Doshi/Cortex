"""Reproducible Benchmark Script for Cortex Multi-Agent DAG Execution.

Compares sequential execution vs ThreadPoolExecutor concurrent execution on identical inputs,
verifying output equivalence first and logging raw timing distributions (mean, p50, p95).
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.executor import executor  # noqa: E402
from backend.models import ExecutionPlan, ToolStep  # noqa: E402
from backend.tools import TOOL_REGISTRY  # noqa: E402


def generate_benchmark_dataset(filename: str = "benchmark_data.csv", rows: int = 20000) -> str:
    """Generate a reproducible synthetic dataset for benchmarking."""
    np.random.seed(42)
    departments = ["Engineering", "HR", "Sales", "Marketing", "Product", "Operations"]
    genders = ["Male", "Female", "Non-Binary"]
    
    data = {
        "employee_id": list(range(1, rows + 1)),
        "age": np.random.randint(22, 65, size=rows),
        "department": np.random.choice(departments, size=rows),
        "gender": np.random.choice(genders, size=rows),
        "salary": np.random.normal(85000, 25000, size=rows).round(2),
        "years_experience": np.random.randint(1, 40, size=rows),
        "performance_score": np.random.uniform(1.0, 5.0, size=rows).round(2),
    }
    
    df = pd.DataFrame(data)
    filepath = PROJECT_ROOT / "outputs" / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    return str(filepath)


def build_benchmark_plan(filepath: str) -> ExecutionPlan:
    """Construct a multi-branch DAG execution plan with independent steps.
    
    DAG Structure:
      - profile_1 (no dep)
      - exec_dept (no dep) -> visualize_dept (dep: exec_dept)
      - exec_hist (no dep) -> visualize_hist (dep: exec_hist)
      - exec_corr (no dep)
      - analyze_1 (dep: visualize_dept, visualize_hist, exec_corr, profile_1)
    """
    steps = [
        ToolStep(
            id="profile_1",
            tool="profile",
            dependencies=[],
            description="Profile dataset schema and quality",
            why="Initial dataset profiling",
        ),
        ToolStep(
            id="exec_dept",
            tool="execute_python",
            dependencies=[],
            operation="groupby_department_mean",
            description="Compute department average salaries",
            why="Department salary aggregation",
        ),
        ToolStep(
            id="exec_hist",
            tool="execute_python",
            dependencies=[],
            operation="histogram",
            description="Compute salary distribution histogram",
            why="Histogram analysis",
        ),
        ToolStep(
            id="exec_corr",
            tool="execute_python",
            dependencies=[],
            operation="correlation_matrix",
            description="Compute numerical correlation matrix",
            why="Correlation analysis",
        ),
        ToolStep(
            id="visualize_dept",
            tool="visualize",
            dependencies=["exec_dept"],
            chart_type="bar",
            description="Generate bar chart spec for department salaries",
            why="Department salary visualization",
        ),
        ToolStep(
            id="visualize_hist",
            tool="visualize",
            dependencies=["exec_hist"],
            chart_type="histogram",
            description="Generate histogram chart spec",
            why="Histogram visualization",
        ),
        ToolStep(
            id="analyze_1",
            tool="analyze",
            dependencies=["profile_1", "visualize_dept", "visualize_hist", "exec_corr"],
            description="Synthesize final investigation findings",
            why="Final analysis step",
        ),
    ]

    plan = ExecutionPlan(
        goal="Benchmark evaluation of multi-branch DAG",
        reasoning="Reproducible benchmark plan",
        confidence=1.0,
        steps=steps,
        expected_outputs="Complete analytics & visual specs",
    )
    object.__setattr__(plan, "file_path", filepath)
    return plan


def run_sequential_execution(plan: ExecutionPlan, execution_id: str) -> tuple[float, dict]:
    """Execute steps 100% sequentially on the main thread in topological order."""
    sorted_steps = executor._topological_sort(plan.steps)
    step_outputs = {}
    
    t0 = time.perf_counter()
    for step in sorted_steps:
        dep_outputs = {dep_id: step_outputs[dep_id] for dep_id in step.dependencies if dep_id in step_outputs}
        handler = TOOL_REGISTRY[step.tool]
        output = handler(
            file_path=plan.file_path,
            dependency_outputs=dep_outputs,
            execution_id=execution_id,
            **step.params,
        )
        step_outputs[step.id] = output
    t1 = time.perf_counter()
    
    duration_ms = (t1 - t0) * 1000.0
    return duration_ms, step_outputs


def run_concurrent_execution(plan: ExecutionPlan, execution_id: str) -> tuple[float, dict]:
    """Execute steps concurrently using ToolExecutor's ThreadPoolExecutor."""
    t0 = time.perf_counter()
    result = executor.execute(plan, execution_id=execution_id)
    t1 = time.perf_counter()
    
    duration_ms = (t1 - t0) * 1000.0
    step_outputs = {r.step_id: r.output for r in result.results if r.success}
    return duration_ms, step_outputs


def verify_output_equivalence(seq_outputs: dict, conc_outputs: dict) -> bool:
    """Verify that sequential and concurrent outputs are byte/dict equivalent."""
    keys_match = set(seq_outputs.keys()) == set(conc_outputs.keys())
    if not keys_match:
        return False
    for step_id in seq_outputs:
        if seq_outputs[step_id] != conc_outputs[step_id]:
            return False
    return True


def run_benchmark(repetitions: int = 10, dataset_rows: int = 20000) -> dict:
    """Run full reproducible benchmark suite."""
    print("=" * 60)
    print("CORTEX MULTI-AGENT DAG BENCHMARK SUITE")
    print("=" * 60)
    
    print(f"Generating synthetic dataset ({dataset_rows} rows)...")
    filepath = generate_benchmark_dataset(rows=dataset_rows)
    plan = build_benchmark_plan(filepath)
    
    print("Verifying output equivalence across execution modes...")
    seq_time_warmup, seq_out_warmup = run_sequential_execution(plan, "benchmark_warmup_seq")
    conc_time_warmup, conc_out_warmup = run_concurrent_execution(plan, "benchmark_warmup_conc")
    
    is_equivalent = verify_output_equivalence(seq_out_warmup, conc_out_warmup)
    print(f"Output Equivalence Verified: {is_equivalent}")
    if not is_equivalent:
        raise ValueError("Sequential and Concurrent execution produced divergent outputs!")

    seq_timings = []
    conc_timings = []
    
    print(f"Running {repetitions} benchmark repetitions...")
    for i in range(1, repetitions + 1):
        seq_ms, _ = run_sequential_execution(plan, f"benchmark_seq_{i}")
        conc_ms, _ = run_concurrent_execution(plan, f"benchmark_conc_{i}")
        seq_timings.append(seq_ms)
        conc_timings.append(conc_ms)
        print(f"  Repetition {i:02d}/{repetitions}: Sequential = {seq_ms:.2f}ms | Concurrent = {conc_ms:.2f}ms | Ratio = {seq_ms / conc_ms:.2f}x")

    seq_arr = np.array(seq_timings)
    conc_arr = np.array(conc_timings)
    
    mean_seq = float(np.mean(seq_arr))
    mean_conc = float(np.mean(conc_arr))
    p50_seq = float(np.median(seq_arr))
    p50_conc = float(np.median(conc_arr))
    p95_seq = float(np.percentile(seq_arr, 95))
    p95_conc = float(np.percentile(conc_arr, 95))
    
    speedup_mean = mean_seq / mean_conc if mean_conc > 0 else 1.0
    speedup_p50 = p50_seq / p50_conc if p50_conc > 0 else 1.0

    print("-" * 60)
    print("BENCHMARK SUMMARY RESULTS:")
    print(f"  Sequential Mean Duration : {mean_seq:.2f} ms (p50: {p50_seq:.2f} ms, p95: {p95_seq:.2f} ms)")
    print(f"  Concurrent Mean Duration : {mean_conc:.2f} ms (p50: {p50_conc:.2f} ms, p95: {p95_conc:.2f} ms)")
    print(f"  Empirical Speedup Ratio  : {speedup_mean:.2f}x (p50: {speedup_p50:.2f}x)")
    print("=" * 60)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "os": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor() or "Unknown",
            "cpu_count": os.cpu_count(),
            "pandas_version": pd.__version__,
        },
        "benchmark_config": {
            "dataset_rows": dataset_rows,
            "dag_steps_count": len(plan.steps),
            "worker_threads": 4,
            "repetitions": repetitions,
            "output_equivalent": is_equivalent,
        },
        "results": {
            "sequential": {
                "raw_timings_ms": [round(t, 2) for t in seq_timings],
                "mean_ms": round(mean_seq, 2),
                "p50_ms": round(p50_seq, 2),
                "p95_ms": round(p95_seq, 2),
            },
            "concurrent": {
                "raw_timings_ms": [round(t, 2) for t in conc_timings],
                "mean_ms": round(mean_conc, 2),
                "p50_ms": round(p50_conc, 2),
                "p95_ms": round(p95_conc, 2),
            },
            "speedup_ratio_mean": round(speedup_mean, 2),
            "speedup_ratio_p50": round(speedup_p50, 2),
        },
    }

    output_file = PROJECT_ROOT / "docs" / "benchmark_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved raw benchmark results to {output_file}")
    
    return report


if __name__ == "__main__":
    run_benchmark(repetitions=10, dataset_rows=20000)
