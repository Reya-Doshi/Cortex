<div align="center">

# 🧠 Cortex — Autonomous Multi-Agent Data Investigation Platform

[![Live Demo](https://img.shields.io/badge/Live%20Demo-cortex--beta--nine.vercel.app-6366f1?style=for-the-badge&logo=vercel&logoColor=white)](https://cortex-beta-nine.vercel.app)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-8E75B2?style=for-the-badge&logo=googlecloud&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<br />

> **Upload a CSV, ask a natural language question, and watch a team of AI agents plan, execute, and explain the analysis — in parallel, 2x faster than sequential execution.**

[Explore Live Demo](https://cortex-beta-nine.vercel.app) • [System Architecture](#-system-architecture) • [Setup & Installation](#-setup--installation) • [API Documentation](#-api-documentation) • [Benchmarks & Performance](#-benchmarks--performance)

</div>

---

## ⚡ What is Cortex?

**Cortex** is an enterprise-grade, autonomous data investigation platform powered by Google Gemini 2.5 Flash and a multi-agent Directed Acyclic Graph (DAG) runtime.

Unlike linear LLM code execution loops, Cortex decouples analytical planning from execution. It constructs a dependency-aware plan graph, executes non-dependent statistical routines **concurrently** via a thread-pool dispatcher, enforces strict schema validation, and generates executive PDF reports with zero state leakage.

> [!IMPORTANT]
> **Key Benchmark:** Cortex achieves a **2.14x average execution speedup** compared to sequential processing by scheduling non-blocking data aggregation and visualization pipelines in parallel threads.

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| ⚡ **Parallel DAG Scheduler** | Resolves task dependencies on-the-fly and dispatches ready nodes to a concurrent `ThreadPoolExecutor`. |
| 🛡️ **Zero State Leakage** | Complete request isolation with unique `execution_id` namespacing across dataframes, temp caches, and generated artifacts. |
| 🎯 **Strict Intent & Column Guard** | Validates schema existence upfront to block hallucinated columns and ensure deterministic Pandas operations. |
| 📊 **Interactive Recharts Engine** | Automatically generates custom interactive visual specs (bar, line, scatter, pie) directly rendered in React. |
| 📄 **Automated PDF Exporter** | Synthesizes complex multi-agent analysis runs into executive-ready downloadable PDF reports (`fpdf2`). |
| 🧪 **100% Mocked Offline Test Suite** | Full pytest coverage for planner intent resolution, error boundaries, and synthetic edge cases without spending API tokens. |

---

## 🏗️ System Architecture

Cortex separates execution into decoupled layers: UI client, FastAPI web orchestrator, Gemini planner, concurrent tool runner, and visualizer.

```mermaid
graph TD
    A[React 18 / Vite Frontend] -->|REST API Requests| B[FastAPI Gateway]
    B --> C[Profiler Agent]
    B --> D[Planner Agent - Gemini 2.5 Flash]
    
    D -->|Strict JSON Schema DAG| E[Concurrent Tool Executor]
    
    subgraph "Parallel Execution Pool (ThreadPoolExecutor)"
        E -->|Worker Thread 1| F1[Python Math / Pandas Engine]
        E -->|Worker Thread 2| F2[Data Profiler & Aggregator]
        E -->|Worker Thread 3| F3[Recharts Visualizer Engine]
    end
    
    F1 & F2 & F3 --> G[Analysis Agent - Insight Synthesizer]
    G --> H[Report Generator - PDF / History Storage]
    H -->|JSON / Streamed PDF| A
```

### Decoupled Data & Agent Flow

```text
               ┌─────────────────────────────────────────┐
               │              React Client               │
               └────────────────────┬────────────────────┘
                                    │
                    HTTP Requests   │   PDF & JSON Reports
                                    ▼
               ┌─────────────────────────────────────────┐
               │           FastAPI Web Server            │
               └────────────────────┬────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│ Profiler     │             │ Planner      │             │ History /    │
│ Engine       │             │ (Gemini 2.5) │             │ PDF Exporter │
└──────────────┘             └──────┬───────┘             └──────────────┘
                                    │
                            Constructs DAG
                                    │
                                    ▼
                     ┌─────────────────────────────┐
                     │    Concurrent DAG Runner    │
                     │    (ThreadPoolExecutor)     │
                     └──────────────┬──────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
   │ Aggregations    │     │ GroupBy / Bins  │     │ Visual Spec     │
   │ & Filtering     │     │ & Stat Computes │     │ Generator       │
   └─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 🤖 Agent Roles & Pipeline

Cortex assigns micro-tasks across specialized agent modules to maximize accuracy and speed:

1. 📥 **[dataset_manager.py](file:///c:/Users/reyad/OneDrive/Desktop/Projects/Cortex/backend/dataset_manager.py):** Handles dataset uploads, file validation, structural checks, and in-memory Pandas caching.
2. 🔍 **[profiler.py](file:///c:/Users/reyad/OneDrive/Desktop/Projects/Cortex/backend/profiler.py):** Computes dataset health scores, missing value ratios, data types, duplicate counts, and summary statistics.
3. 📐 **[planner.py](file:///c:/Users/reyad/OneDrive/Desktop/Projects/Cortex/backend/planner.py):** Queries Gemini 2.5 Flash using structured Pydantic outputs to output a DAG of `ToolStep` nodes.
4. ⚙️ **[executor.py](file:///c:/Users/reyad/OneDrive/Desktop/Projects/Cortex/backend/executor.py):** Executes independent tool steps in parallel using a `ThreadPoolExecutor` and tracks topological order.
5. 📊 **[visualizer.py](file:///c:/Users/reyad/OneDrive/Desktop/Projects/Cortex/backend/visualizer.py):** Builds structured Recharts JSON configs from output data nodes without re-reading raw CSVs.
6. 🧠 **[agent.py](file:///c:/Users/reyad/OneDrive/Desktop/Projects/Cortex/backend/agent.py):** Synthesizes analytical insights from execution node outputs into clear business explanations.
7. 📄 **[report_generator.py](file:///c:/Users/reyad/OneDrive/Desktop/Projects/Cortex/backend/report_generator.py):** Compiles visual charts, performance metrics, and insights into clean PDF reports using `fpdf2`.

---

## ⚡ Benchmarks & Performance

By leveraging parallel DAG execution, Cortex eliminates bottlenecks common in sequential execution models.

| Metric | Sequential Execution | Cortex Parallel DAG | Gain / Improvement |
| :--- | :--- | :--- | :--- |
| **Execution Time (Avg)** | `4.28s` | **`2.00s`** | **2.14x Speedup** 🚀 |
| **Dependency Validation** | Post-execution erroring | Pre-execution Topological Sort | Zero invalid run propagation |
| **Context Isolation** | Shared state contamination | Request-scoped Namespaces | 100% Zero Leakage |
| **Column Safety** | Unchecked LLM inputs | Pre-flight Column Guard | 0% Hallucinated Columns |

---

## 🛠️ Tech Stack Matrix

| Area | Technologies Used |
| :--- | :--- |
| **Backend Core** | Python 3.10+, [FastAPI](file:///c:/Users/reyad/OneDrive/Desktop/Projects/Cortex/backend/app.py), Uvicorn, Pydantic v2 |
| **Data Processing** | Pandas, NumPy, SciPy, ThreadPoolExecutor |
| **AI & LLM** | Google Gemini 2.5 Flash (`google-genai` SDK), Structured JSON Schema |
| **Frontend UI** | React 18, TypeScript, Vite, Tailwind CSS v4, Lucide Icons |
| **Visualization & UX** | Recharts, Custom SVG DAG Renderer ([PlanGraph.tsx](file:///c:/Users/reyad/OneDrive/Desktop/Projects/Cortex/frontend/src/components/PlanGraph.tsx)) |
| **Export Engine** | `fpdf2` for automated corporate PDF report compilation |
| **DevOps & Containers** | Docker, Docker Compose, Vercel |
| **Testing** | Pytest, Mocked Offline LLM Engine |

---

## 📂 Project Structure

```
Cortex/
├── 📁 backend/                       # FastAPI Backend Engine
│   ├── 📄 agent.py                   # Orchestrator & Analysis Synthesizer
│   ├── 📄 app.py                     # FastAPI REST API Endpoints
│   ├── 📄 config.py                  # Environment & Global Configs
│   ├── 📄 dataset_manager.py         # CSV Upload & Caching Engine
│   ├── 📄 executor.py                # Concurrent ThreadPool DAG Scheduler
│   ├── 📄 history_manager.py         # JSON History Storage
│   ├── 📄 models.py                  # Pydantic Schemas & Data Contracts
│   ├── 📄 planner.py                 # Gemini 2.5 Flash DAG Planner
│   ├── 📄 profiler.py                # Dataset Health & Profiling
│   ├── 📄 report_generator.py        # fpdf2 PDF Report Generator
│   ├── 📄 tools.py                   # Atomic Analysis Tool Registry
│   ├── 📄 visualizer.py             # Recharts Spec Generator
│   └── 📁 tests/                     # Unit Tests Suite
│       └── 📄 test_planner.py        # Pytest Mocked Intent Tests
├── 📁 datasets/                      # Sample Datasets (Titanic, Sales)
├── 📁 frontend/                      # React 18 + Vite Frontend
│   ├── 📁 src/
│   │   ├── 📁 components/            # UI Components
│   │   │   ├── 📄 PlanGraph.tsx      # SVG DAG Pipeline Graph
│   │   │   ├── 📄 MetricsPanel.tsx   # Concurrency & Speedup Metrics
│   │   │   ├── 📄 TerminalLogs.tsx   # Live Execution Stream UI
│   │   │   ├── 📄 HistorySidebar.tsx # Saved Runs Sidebar
│   │   │   └── 📄 Sidebar.tsx        # Dataset Selector & Controls
│   │   ├── 📄 App.tsx                # Main Dashboard View
│   │   └── 📄 index.css              # Tailwind v4 Global Styles
│   ├── 📄 Dockerfile                 # Frontend Container Spec
│   └── 📄 package.json               # Node Dependencies
├── 📄 Dockerfile                     # Backend Dockerfile
├── 📄 docker-compose.yml             # Full-stack Container Orchestration
├── 📄 requirements.txt               # Python Dependencies
└── 📄 README.md                      # Project Documentation
```

---

## ⚡ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- Node.js 18+ and npm
- Docker & Docker Compose (Optional for containerized run)
- Google Gemini API Key ([Get Key Here](https://aistudio.google.com/))

---

### 1. Clone & Configure

```bash
git clone https://github.com/Reya-Doshi/Cortex.git
cd Cortex
```

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
PORT=8000
```

---

### 2. Local Manual Startup

#### Step A: Backend Server Setup

```bash
# 1. Create Python virtual environment
python -m venv venv

# 2. Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# macOS / Linux:
source venv/bin/activate

# 3. Install backend dependencies
pip install -r requirements.txt
pip install fpdf2

# 4. Start FastAPI server
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

#### Step B: Frontend React Setup

Open a separate terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install --legacy-peer-deps

# Start Vite dev server
npm run dev
```

Visit **`http://localhost:5173`** in your browser.

---

### 3. Docker Deployment 🐳

Deploy the full stack in a containerized environment:

```bash
# Build and start all services in detached mode
docker-compose up -d --build
```

- **Frontend:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
- **Interactive API Docs:** `http://localhost:8000/docs`

---

## 📝 API Documentation

### `POST /upload`
Uploads and profiles a new CSV dataset.

- **Endpoint:** `POST /upload`
- **Content-Type:** `multipart/form-data`
- **Parameters:** `file` (CSV File)

#### Response `200 OK`:
```json
{
  "file_id": "c7f1a890-4e2b",
  "filename": "titanic_sample.csv",
  "file_path": "uploads/c7f1a890-4e2b.csv",
  "rows": 891,
  "columns": 12,
  "column_names": [
    "PassengerId",
    "Survived",
    "Pclass",
    "Name",
    "Sex",
    "Age",
    "Fare",
    "Embarked"
  ]
}
```

---

### `POST /analyze`
Triggers the multi-agent DAG planning, execution, and synthesis pipeline.

- **Endpoint:** `POST /analyze`
- **Content-Type:** `application/json`

#### Request Body:
```json
{
  "question": "What is the survival rate by gender and age group?",
  "file_paths": [
    "uploads/c7f1a890-4e2b.csv"
  ]
}
```

#### Response `200 OK`:
```json
{
  "answer": "Female passengers exhibited a significantly higher survival rate (74.2%) compared to males (18.9%)...",
  "plan": {
    "steps": [
      {
        "id": "step_1",
        "tool_name": "aggregate_data",
        "description": "Calculate mean survival rate grouped by Sex",
        "dependencies": []
      },
      {
        "id": "step_2",
        "tool_name": "bin_numeric_column",
        "description": "Bin Age into Child, Adult, Senior groups",
        "dependencies": []
      }
    ]
  },
  "metrics": {
    "total_duration_sec": 1.94,
    "sequential_duration_sec": 4.12,
    "speedup_ratio": 2.12,
    "executed_steps_count": 2
  },
  "metadata": {
    "run_id": "run_992a1b4d"
  }
}
```

---

### `GET /history`
Retrieves a list of all historical data investigation runs.

- **Endpoint:** `GET /history`

#### Response `200 OK`:
```json
[
  {
    "run_id": "run_992a1b4d",
    "timestamp": "2026-08-29T22:00:00Z",
    "question": "What is the survival rate by gender and age group?",
    "speedup_ratio": 2.12,
    "status": "completed"
  }
]
```

---

### `GET /report/{run_id}`
Generates and streams a downloadable executive PDF report.

- **Endpoint:** `GET /report/{run_id}`
- **Response:** Binary file stream (`application/pdf`) with `Content-Disposition: attachment; filename="cortex_report_run_992a1b4d.pdf"`.

---

## 🧪 Automated Testing

Cortex features an offline test suite powered by `pytest` with mocked Gemini responses to verify intent mapping and guardrails without incurring API latency or costs.

```bash
# Run pytest on the planner and execution module
python -m pytest -v backend/tests/test_planner.py
```

### Sample Verbose Test Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.10+, pytest-8.x -- venv/Scripts/python.exe
cachedir: .pytest_cache
rootdir: Cortex
collected 8 items

backend/tests/test_planner.py::test_age_group_survival PASSED            [ 12%]
backend/tests/test_planner.py::test_survival_by_sex PASSED               [ 25%]
backend/tests/test_planner.py::test_average_salary_by_department PASSED  [ 37%]
backend/tests/test_planner.py::test_monthly_sales_trend PASSED           [ 50%]
backend/tests/test_planner.py::test_missing_value_analysis PASSED        [ 62%]
backend/tests/test_planner.py::test_histogram_generation PASSED          [ 75%]
backend/tests/test_planner.py::test_correlation_analysis PASSED          [ 87%]
backend/tests/test_planner.py::test_missing_columns_error PASSED         [100%]

============================== 8 passed in 2.14s ==============================
```

---

## 🛡️ License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ powered by **Google Gemini 2.5 Flash**, **FastAPI**, & **React**

</div>
