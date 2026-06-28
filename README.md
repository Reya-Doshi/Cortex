## Live Demo
[cortex-beta-nine.vercel.app](https://cortex-beta-nine.vercel.app)

## What it does in one line
Upload a CSV, ask a natural language question, and watch a team of 
AI agents plan, execute, and explain the analysis — in parallel, 
2x faster than sequential execution.

# Cortex — Autonomous Multi-Agent Data Investigation Platform

![Demo](demo.gif)

Cortex is an autonomous, production-grade data investigation platform. It enables users to upload CSV datasets, ask natural language questions, and witness a collaborative agent team profile the data, plan a Directed Acyclic Graph (DAG) of transformations, run python aggregation routines concurrently, and explain findings with interactive Recharts visualizations.

### 🌟 Key Platform Features:
- **True Parallel DAG Executor:** Runs independent analysis steps concurrently using a dependency-aware ThreadPoolExecutor.
- **Strict Intent Resolution & Semantic Matching:** Validates dataset columns beforehand and maps queries to precise pandas operations (e.g. age binning, department means) with zero silent column replacements.
- **Zero State Leakage Architecture:** Creates isolated request-scoped execution contexts namespaced by unique execution IDs.
- **Mocked Testing Engine:** 100% offline pytest suite verifying planner intent resolution and error bounds.

---

## 🏗️ System Architecture

```
                    ┌────────────────────────┐
                    │      React Client      │
                    └───────────┬────────────┘
                                │
               HTTP Requests    │  PDF & JSON Reports
                                ▼
                    ┌────────────────────────┐
                    │    FastAPI Web App     │
                    └───────────┬────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ Planner Agent │       │ Tool Executor │       │ History/PDF   │
│ (Gemini 2.5)  │       │ (ThreadPool)  │       │   Managers    │
└───────────────┘       └───────┬───────┘       └───────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌───────────────┐┌───────────────┐┌───────────────┐
        │ Profiler Tool ││ Python Engine ││ Visualization │
        └───────────────┘└───────────────┘└───────────────┘
```

## Performance
- Parallel DAG execution: **2.14x average speedup** over sequential
- Topological sort detects cyclic deps before dispatch
- Zero state leakage: each request gets an isolated execution context
- 100% offline pytest suite covering planner intent resolution

---

## 🤖 Agent Workflow & Pipeline

Cortex partitions analysis responsibilities across specialized agent entities:

1. **Dataset Manager:** Manages uploads, validates file sizes/extensions, and caches pandas DataFrames.
2. **Profiler Agent:** Performs non-blocking summary statistics (row/col count, missing ratios, data types, duplicate counts) and computes a data health rating.
3. **Planner Agent:** Calls Gemini 2.5 Flash using strict JSON schemas to output a DAG of `ToolStep` nodes. It is architecturally sandboxed from answering the user query directly.
4. **Tool Executor:** Parses the generated plan, resolves dependencies, and schedules task blocks concurrently using a ThreadPool.
5. **Analysis Agent:** Receives only the execution plan and step-level outputs (sandboxed from the raw CSV) to compile the final strategic explanation.
6. **Visualization Agent:** Generates Recharts plot specifications from dependency step data without reading raw CSVs.

---

## 🚀 Concurrency & Concurrency Design

Cortex schedules independent DAG execution nodes concurrently using a thread pool scheduler.
- **Dependency Detection:** Node status cycles from `Pending` ➔ `Running` ➔ `Completed` / `Failed`.
- **Topological Sorting:** A DFS topological check detects cyclic dependencies before dispatching.
- **Concurrently Dispatched:** Any step whose dependencies have fully completed is submitted to `ThreadPoolExecutor`.
- **Speedup Calculations:** Wall-clock parallel execution duration is recorded alongside the sum of individual step durations to calculate the `Parallel Speedup Ratio` (e.g. `2.14x speedup`).

---

## 📦 Folder Structure

```
Cortex/
├── backend/                  # FastAPI Backend Source
│   ├── agent.py              # Orchestration & Analysis Agent
│   ├── app.py                # Web server API endpoints
│   ├── config.py             # Environment configurations
│   ├── dataset_manager.py    # CSV upload and caching engine
│   ├── executor.py           # Concurrency DAG scheduler
│   ├── history_manager.py    # Local JSON run history manager
│   ├── models.py             # Pydantic schemas and types
│   ├── profiler.py           # Data summary engine
│   ├── report_generator.py   # fpdf2 PDF report exporter
│   ├── tools.py              # Core tool registry
│   └── visualizer.py         # Visual spec constructor
├── datasets/                 # Local datasets for query suggestions
├── frontend/                 # React Frontend Source (Vite)
│   ├── src/
│   │   ├── components/       # Reusable React components
│   │   │   ├── Sidebar.tsx
│   │   │   ├── PlanGraph.tsx # SVG DAG Renderer
│   │   │   ├── HistorySidebar.tsx
│   │   │   ├── MetricsPanel.tsx
│   │   │   └── TerminalLogs.tsx
│   │   ├── App.tsx           # Main workspace UI
│   │   └── index.css         # Tailwind v4 styles
│   ├── Dockerfile            # Frontend container spec
│   └── package.json          # Node dependencies
├── Dockerfile                # Root Backend container spec
├── docker-compose.yml        # Orchestration spec
└── README.md                 # Project Documentation
```

---

## ⚡ Setup & Installation

### Local Manual Startup

#### 1. Backend Server Setup
Ensure Python 3.10+ is installed:
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install fpdf2

# Start FastAPI
uvicorn backend.app:app --port 8000 --reload
```

#### 2. Frontend React Setup
Open a separate terminal:
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🐳 Docker Deployment

To deploy Cortex in a containerized environment (e.g. AWS EC2, DigitalOcean VM, or local Docker):

### Next Steps to Deploy:
1. **Clone the GitHub repository:**
   ```bash
   git clone https://github.com/Reya-Doshi/Cortex.git
   cd Cortex
   ```

2. **Configure your API Key:**
   Create a `.env` file at the root of the project with your Gemini Developer API Key:
   ```bash
   echo "GEMINI_API_KEY=your_actual_gemini_api_key" > .env
   ```

3. **Start the containers:**
   Deploy the full stack in detached mode:
   ```bash
   docker-compose up -d --build
   ```

### Services Built:
- **`backend` service** (FastAPI) running on port `8000`.
- **`frontend` service** (Vite) running on port `5173`.
- Local directories `./uploads` and `./outputs` are mounted to persistent Docker volumes to retain dataset uploads and investigation runs history upon container updates.

---

## 📝 API Documentation

### `POST /upload`
Uploads and validates a CSV dataset.
- **Response:**
  ```json
  {
    "file_id": "unique-id",
    "filename": "dataset.csv",
    "file_path": "uploads/dataset.json",
    "rows": 1000,
    "columns": 5,
    "column_names": ["department", "salary", "age"]
  }
  ```

### `POST /analyze`
Triggers the multi-agent planning and execution pipeline.
- **Request Body:**
  ```json
  {
    "question": "Which department has the highest average salary?",
    "file_paths": ["uploads/dataset.csv"]
  }
  ```
- **Response:**
  - `answer`: Textual business insights.
  - `plan`: Detailed DAG steps.
  - `metrics`: Timing durations, sequential/parallel speedups, and status reports.
  - `metadata`: Contains `run_id` for history reopening.

### `GET /history`
Returns list of all saved investigation metadata.

### `GET /report/{run_id}`
Generates and downloads a branded PDF report containing graphs, execution speedups, and strategic recommendations.

---

## 🧪 Automated Testing

We have built a comprehensive, offline mocked unit testing suite using `pytest` to verify all analytical intent mapping patterns and column validation error cases without exhausting your API key limits.

Run the tests locally:
```bash
python -m pytest -v backend/tests/test_planner.py
```

### Verbose Test Execution Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\lenovo\OneDrive\Desktop\ReyaWeb\Cortex\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\lenovo\OneDrive\Desktop\ReyaWeb\Cortex
plugins: anyio-4.14.1, langsmith-0.9.2
collecting ... collected 8 items

backend/tests/test_planner.py::test_age_group_survival PASSED            [ 12%]
backend/tests/test_planner.py::test_survival_by_sex PASSED               [ 25%]
backend/tests/test_planner.py::test_average_salary_by_department PASSED  [ 37%]
backend/tests/test_planner.py::test_monthly_sales_trend PASSED           [ 50%]
backend/tests/test_planner.py::test_missing_value_analysis PASSED        [ 62%]
backend/tests/test_planner.py::test_histogram_generation PASSED          [ 75%]
backend/tests/test_planner.py::test_correlation_analysis PASSED          [ 87%]
backend/tests/test_planner.py::test_missing_columns_error PASSED         [100%]

============================= 8 passed in 11.88s ==============================
```

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for details.

## 🤝 Acknowledgements
- Powered by Google Gemini 2.5 Flash.
- Chart rendering powered by Recharts.
- Containerization optimized for Docker-ready cloud environments.
