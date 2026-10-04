# Cortex System Verification & Claim Audit

**Reviewed Commit:** `31fcf10`  
**Date:** October 4, 2026  
**Environment:** Windows 11 (Python 3.14.6, pytest 9.1.1, pandas 3.0.6, FastAPI 0.142.2)  

---

## 1. Feature & Claim Audit Table

| Category | Documented Claim / Headline | Source File & Location | Verification Evidence | Audited Status | Required Correction / Resolution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Performance** | "2.14x average execution speedup" (README) / "3.5x speedup" (Portfolio/Resume) | `README.md`, `backend/executor.py#L20-L160` | Ran `docs/benchmark.py` across 10 repetitions on 20,000-row synthetic dataset (4 thread workers). Verified output equivalence (True). Raw Mean: Sequential = `61.17 ms`, Concurrent = `77.94 ms` (Ratio: `0.78x`). | **Unsupported / Corrected** | In-process Python `ThreadPoolExecutor` on CPU-bound Pandas operations suffers from GIL contention & thread scheduling overhead. Speedups only occur when tools wait on non-blocking network/IO calls (e.g. external APIs). Remove unverified speedup percentages from README headline and state realistic GIL limitations. |
| **Security / Sandbox** | "Sandboxed Execution", "Zero State Leakage", "Strict AST Schema Guard" | `backend/dataset_manager.py#L78-L112`, `backend/planner.py#L25-L71`, `backend/tools.py#L38-L182` | `dataset_manager.py` namespaces DataFrame caches with `f"{execution_id}:{path}"` preventing cross-request cache collisions. `planner.py` uses string substring matching (`validate_intent_columns`), not AST parsing. `tools.py` uses predefined Enum functions (`groupby_sex`, `groupby_age_bins`), not dynamic `exec()` or container sandboxes. | **Implemented with Caveats** | Clarify that request isolation is achieved via UUID-namespaced caching, and safety is achieved via a hardcoded registry of predefined Pandas operations rather than OS/container sandboxing or AST parsing. |
| **AI Accuracy** | "100% Mocked Offline Test Suite", accuracy assertions | `backend/tests/test_planner.py` | 8 planner intent tests pass using mocked Gemini JSON schemas. 14 new edge-case behavioral & isolation tests added (total 22/22 passing). No benchmark evaluation dataset exists. | **Implemented (Mocked Unit Tests)** | Keep unit test claims focused on 22/22 deterministic passing pytest cases. Avoid claiming percentage accuracy without a labeled benchmark dataset and evaluation harness. |
| **PDF Reporting** | Automated corporate PDF report exporter | `backend/report_generator.py#L52-L197`, `backend/app.py#L188-L198` | Verified `fpdf2` PDF generation endpoint (`GET /report/{run_id}`) fetches history JSON, renders formatted metadata, step tables, and streams binary PDF. | **Verified** | Accurately document as an implemented feature. |
| **Dataset Upload** | CSV validation, sizing, namespacing | `backend/dataset_manager.py#L140-L181` | Uploads validate `.csv` extension, enforce 50 MB limit, sanitize filenames, store to `uploads/`, and register metadata. | **Verified** | Accurately document. |

---

## 2. Test Execution Log

**Command:**
```bash
.\venv\Scripts\python.exe -m pytest -v
```

**Results:** `22 passed in 0.86s`

### Test Suite Breakdown:

1. `backend/tests/test_planner.py` (8 tests)
   - `test_age_group_survival`: PASSED
   - `test_survival_by_sex`: PASSED
   - `test_average_salary_by_department`: PASSED
   - `test_monthly_sales_trend`: PASSED
   - `test_missing_value_analysis`: PASSED
   - `test_histogram_generation`: PASSED
   - `test_correlation_analysis`: PASSED
   - `test_missing_columns_error`: PASSED

2. `backend/tests/test_pipeline_behavior.py` (9 tests)
   - `test_empty_csv_file_raises_value_error`: PASSED
   - `test_no_rows_csv_raises_value_error`: PASSED
   - `test_invalid_extension_raises_value_error`: PASSED
   - `test_profiler_handles_null_values_correctly`: PASSED
   - `test_validate_intent_columns_detects_missing_age`: PASSED
   - `test_validate_intent_columns_passes_when_present`: PASSED
   - `test_tool_execute_python_unsupported_operation_fallback`: PASSED
   - `test_tool_visualize_handles_empty_or_missing_dependency`: PASSED
   - `test_planner_fallback_on_malformed_llm_response`: PASSED

3. `backend/tests/test_isolation_and_dag.py` (5 tests)
   - `test_topological_sort_rejects_circular_dependency`: PASSED
   - `test_topological_sort_rejects_nonexistent_dependency`: PASSED
   - `test_executor_handles_cycle_gracefully`: PASSED
   - `test_executor_skips_steps_when_parent_fails`: PASSED
   - `test_concurrent_request_state_isolation`: PASSED

---

## 3. Empirical Benchmark Methodology & Results

**Script Location:** `docs/benchmark.py`  
**Raw Results Output:** `docs/benchmark_results.json`  

### Workload Specification:
- **Dataset:** 20,000 synthetic rows (numerical & categorical attributes: age, department, gender, salary, years_experience, performance_score).
- **DAG Plan (7 Steps):** `profile_1` (independent), `exec_dept` (independent), `exec_hist` (independent), `exec_corr` (independent), `visualize_dept` (depends on `exec_dept`), `visualize_hist` (depends on `exec_hist`), `analyze_1` (depends on all prior steps).
- **Output Equivalence:** Verified 100% byte/dictionary match between sequential and concurrent step outputs before measuring timings.
- **Iterations:** 1 Warmup run + 10 benchmark repetitions.

### Benchmark Data (10 Repetitions):

$$\text{Speedup Ratio} = \frac{\text{Sequential Wall-Clock Duration}}{\text{Concurrent Wall-Clock Duration}}$$

- **Sequential Duration:** Mean = `61.17 ms` | p50 = `61.19 ms` | p95 = `69.68 ms`
- **Concurrent Duration (4 Threads):** Mean = `77.94 ms` | p50 = `70.79 ms` | p95 = `108.42 ms`
- **Measured Speedup:** `0.78x` (Mean) | `0.86x` (p50)

### Engineering Analysis:
Because Python's Global Interpreter Lock (GIL) serializes CPU-bound bytecode execution across threads, running pure in-process Pandas aggregations in a `ThreadPoolExecutor` incurs thread creation, context-switching, and locking overhead (~16.7 ms added overhead on average). Parallel threading provides wall-clock speedup when tasks are I/O bound (e.g., waiting on external HTTP API responses or disk reads), but adds minor overhead for purely CPU-bound in-memory data processing.

---

## 4. Upstream Credit & Authorship

- **Engineered By:** Reya Doshi
- **Framework Dependencies:** FastAPI, Google Gemini 2.5 Flash (`google-genai`), Pandas, NumPy, SciPy, React 18, Vite, Recharts, `fpdf2`.
- **License:** MIT License (`LICENSE`).
