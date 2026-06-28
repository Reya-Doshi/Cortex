# Cortex — Autonomous Multi-Agent Data Investigation Platform

Cortex is an autonomous, production-grade data investigation platform. It enables users to upload multiple CSV datasets, ask natural language questions, and witness a collaborative agent team profile the data, plan a Directed Acyclic Graph (DAG) of transformations, run python aggregation routines concurrently, and explain findings with interactive Recharts visualizations.

This project is built to demonstrate high-quality software engineering, modern React/FastAPI full-stack development, multi-agent LLM orchestration, concurrent graph execution, and professional system design.

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
Run the complete multi-agent pipeline containerized in a single command:
```bash
docker-compose up --build
```
This builds:
- **`backend` service** (FastAPI) on port `8000`.
- **`frontend` service** (Vite Dev Server) on port `5173`.
- Mounts local directory volumes for persistent upload files and investigation run history.

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

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for details.

## 🤝 Acknowledgements
- Powered by Google Gemini 2.5 Flash.
- Chart rendering powered by Recharts.
- Containerization optimized for Docker-ready cloud environments.
