"""Pydantic request and response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response payload for the health check endpoint."""

    status: str = Field(..., examples=["ok"])
    service: str = Field(..., examples=["Cortex"])
    version: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


# ---------------------------------------------------------------------------
# Dataset upload & profiling
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    """Response payload after a successful CSV upload."""

    file_id: str = Field(..., description="Unique identifier for the uploaded file.")
    filename: str = Field(..., description="Sanitized original filename.")
    file_path: str = Field(..., description="Relative path from the project root.")
    rows: int = Field(..., ge=0)
    columns: int = Field(..., ge=0)
    column_names: list[str]


class ProfileRequest(BaseModel):
    """Request payload for dataset profiling."""

    file_path: str = Field(..., min_length=1)


class DatasetProfile(BaseModel):
    """Full statistical profile of a dataset."""

    file_path: str
    rows: int = Field(..., ge=0)
    columns: int = Field(..., ge=0)
    column_names: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
    missing_values_pct: dict[str, float]
    duplicate_rows: int = Field(..., ge=0)
    numeric_summary: dict[str, dict[str, Any]]
    preview: list[dict[str, Any]]


class ProfileResponse(BaseModel):
    """Response payload for dataset profiling."""

    profile: DatasetProfile


# ---------------------------------------------------------------------------
# Multi-agent pipeline
# ---------------------------------------------------------------------------


ToolName = str


class ToolStep(BaseModel):
    """A single step in an execution plan."""

    id: str = Field(..., description="Unique ID for this step, e.g., 'profile_1', 'summary_1'.")
    tool: str = Field(..., description="The name of the tool to invoke.")
    dependencies: list[str] = Field(default_factory=list, description="IDs of steps that must complete before this step can run.")
    description: str = Field(default="", description="A short explanation of what this step does.")
    why: str | None = Field(default=None, description="Detailed explanation of why this step and its operation were selected.")
    
    # Explicit fields for tool arguments to prevent dynamic dict schema errors
    chart_type: str | None = Field(default=None, description="Type of chart for visualization, e.g., 'bar', 'line', 'pie', 'histogram'.")
    operation: str | None = Field(default=None, description="Data operation, e.g., 'groupby_mean', 'summary'.")
    question: str | None = Field(default=None, description="The analysis question or sub-question for this step.")

    @property
    def params(self) -> dict[str, Any]:
        """Convert explicit fields to a generic parameter dictionary."""
        p = {}
        if self.chart_type is not None:
            p["chart_type"] = self.chart_type
        if self.operation is not None:
            p["operation"] = self.operation
        if self.question is not None:
            p["question"] = self.question
        return p


class ExecutionPlan(BaseModel):
    """Structured plan produced by the Planner Agent."""

    goal: str = Field(..., description="The main goal of the execution plan.")
    reasoning: str = Field(..., description="The planner's reasoning for this plan.")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0.")
    steps: list[ToolStep] = Field(..., description="The list of tool steps making up the plan (a dependency graph).")
    expected_outputs: str = Field(..., description="The expected outcomes of the execution plan.")


class ToolResult(BaseModel):
    """Result of executing a single tool step."""

    tool: str
    step_id: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    duration_ms: float | None = None


class ExecutionResult(BaseModel):
    """Aggregated results from the Tool Executor."""

    plan: ExecutionPlan
    results: list[ToolResult]
    total_duration_ms: float = Field(default=0.0, description="Total execution time in milliseconds.")


class AnalysisRequest(BaseModel):
    """Request payload for dataset analysis."""

    question: str = Field(..., min_length=1)
    file_path: str | None = Field(default=None, description="Relative path of the dataset file.")
    file_paths: list[str] = Field(default_factory=list, description="List of relative paths of dataset files.")


class AnalysisResponse(BaseModel):
    """Response payload for dataset analysis."""

    answer: str
    plan: ExecutionPlan | None = None
    metrics: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

