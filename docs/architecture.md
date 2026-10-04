# Cortex System Architecture & Design

Cortex is an autonomous multi-agent data investigation platform engineered by Reya Doshi. It converts natural language data questions into dependency-aware execution plans, executes data transformations, generates chart specifications, and synthesizes strategic explanations.

---

## 1. System Component Overview

```
                                ┌─────────────────────────┐
                                │   React 18 / Vite UI    │
                                └────────────┬────────────┘
                                             │
                             HTTP REST API   │   PDF & JSON Reports
                                             ▼
                                ┌─────────────────────────┐
                                │   FastAPI Web Gateway   │
                                └────────────┬────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             ▼                               ▼                               ▼
    ┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
    │  Profiler Tool  │             │  Planner Agent  │             │ History / Report│
    │ (Data Profiler) │             │ (Gemini 2.5)    │             │    Generators   │
    └─────────────────┘             └────────┬────────┘             └─────────────────┘
                                             │
                                     Strict JSON Schema DAG
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │    Concurrent Tool Executor   │
                             │     (ThreadPoolExecutor)      │
                             └───────────────┬───────────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     ▼                       ▼                       ▼
            ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
            │ Worker Thread 1 │     │ Worker Thread 2 │     │ Worker Thread 3 │
            │ Pandas Engine   │     │ Data Aggregator │     │ Visualizer Spec │
            └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
                     │                       │                       │
                     └───────────────────────┼───────────────────────┘
                                             │
                                             ▼
                                ┌─────────────────────────┐
                                │     Analysis Agent      │
                                │   (Insight Synthesizer) │
                                └─────────────────────────┘
```

---

## 2. Core Modules

1. **Dataset Manager (`backend/dataset_manager.py`)**
   - Validates CSV extensions (`.csv`), file size limits (50 MB default), and filename sanitization.
   - Loads DataFrames into an in-memory cache namespaced by `execution_id` (`f"{execution_id}:{path}"`) to guarantee state isolation across simultaneous requests.

2. **Profiler Agent (`backend/profiler.py`)**
   - Calculates dataset health, row/column counts, data types, missing value ratios (`missing_values_pct`), duplicate counts, numeric summary stats (`describe()`), and 5-row previews.

3. **Planner Agent (`backend/planner.py`)**
   - Performs intent validation (`validate_intent_columns`) to verify column presence before querying the LLM.
   - Invokes Google Gemini 2.5 Flash with Pydantic structured output schemas (`ExecutionPlan`) to produce a Directed Acyclic Graph (DAG) of `ToolStep` nodes.

4. **Tool Executor (`backend/executor.py`)**
   - Performs DFS topological sorting (`_topological_sort`) to detect circular dependencies before execution.
   - Schedules steps dynamically using `concurrent.futures.ThreadPoolExecutor`. Steps whose dependencies have completed run concurrently.
   - If a step fails, dependent downstream steps are skipped cleanly without crashing the process.

5. **Visualization Agent (`backend/visualizer.py`)**
   - Generates interactive Recharts configuration specifications (bar, line, pie, histogram) directly from processed tool step outputs without re-reading raw CSV files.

6. **Analysis Agent (`backend/agent.py`)**
   - Formats execution step outputs and dataset schema context, querying Gemini 2.5 Flash to synthesize human-readable executive explanations.

7. **PDF Exporter (`backend/report_generator.py`)**
   - Compiles investigation metadata, question, execution steps, metrics, and synthesized findings into branded PDF reports using `fpdf2`.
