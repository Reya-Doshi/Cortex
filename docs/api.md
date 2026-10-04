# Cortex API Documentation

The Cortex backend is a FastAPI application exposing REST endpoints for dataset upload, profiling, multi-agent analysis, history retrieval, and PDF report downloads.

---

## Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET / HEAD` | `/health` | Service health check |
| `POST` | `/upload` | Upload and validate a CSV dataset |
| `POST` | `/profile` | Compute dataset statistical profile |
| `POST` | `/analyze` | Execute multi-agent investigation pipeline |
| `GET` | `/history` | List past investigation runs |
| `GET` | `/history/{run_id}` | Get full details of a past run |
| `GET` | `/report/{run_id}` | Download branded PDF report |

---

## Detailed Endpoint Specifications

### 1. `GET /health` & `HEAD /health`
Returns service status and version information. Compatible with Uptime Robot keep-alive pings.

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "service": "Cortex",
  "version": "0.1.0"
}
```

---

### 2. `POST /upload`
Uploads and validates a CSV file.

- **Content-Type:** `multipart/form-data`
- **Body:** `file` (UploadFile, max 50 MB, `.csv` only)

**Response (`200 OK`):**
```json
{
  "file_id": "c7f1a8904e2b",
  "filename": "titanic_sample.csv",
  "file_path": "uploads/c7f1a8904e2b_titanic_sample.csv",
  "rows": 891,
  "columns": 12,
  "column_names": ["PassengerId", "Survived", "Pclass", "Name", "Sex", "Age"]
}
```

---

### 3. `POST /analyze`
Triggers the multi-agent investigation pipeline (Plan → Execute → Explain).

- **Content-Type:** `application/json`

**Request Payload:**
```json
{
  "question": "What is the survival rate by gender and age group?",
  "file_paths": ["uploads/c7f1a8904e2b_titanic_sample.csv"]
}
```

**Response (`200 OK`):**
```json
{
  "answer": "Female passengers exhibited a significantly higher survival rate (74.2%) compared to male passengers (18.9%)...",
  "plan": {
    "goal": "Analyze survival rate by gender and age group",
    "reasoning": "Selected groupby_sex and groupby_age_bins operations",
    "confidence": 0.95,
    "steps": [
      {
        "id": "profile_1",
        "tool": "profile",
        "dependencies": [],
        "description": "Profile dataset"
      },
      {
        "id": "exec_python_1",
        "tool": "execute_python",
        "dependencies": ["profile_1"],
        "operation": "groupby_sex",
        "why": "Calculate survival rate by gender"
      }
    ]
  },
  "metrics": {
    "total_duration_ms": 1940.5,
    "steps": [
      {
        "step_id": "exec_python_1",
        "tool": "execute_python",
        "success": true,
        "duration_ms": 45.2
      }
    ]
  },
  "metadata": {
    "run_id": "a1b2c3d4e5f6",
    "execution_id": "exec_1234567890ab"
  }
}
```

---

### 4. `GET /history`
Lists all saved historical investigation runs ordered newest first.

**Response (`200 OK`):**
```json
{
  "history": [
    {
      "id": "a1b2c3d4e5f6",
      "timestamp": "2026-10-04T14:00:00Z",
      "question": "What is the survival rate by gender and age group?",
      "datasets": ["uploads/c7f1a8904e2b_titanic_sample.csv"],
      "steps_count": 4,
      "total_duration_ms": 1940.5,
      "confidence": 0.95
    }
  ]
}
```

---

### 5. `GET /report/{run_id}`
Compiles and streams a downloadable PDF report.

**Response:** Binary PDF stream (`application/pdf`) with `Content-Disposition: attachment; filename="cortex_report_a1b2c3d4e5f6.pdf"`.
