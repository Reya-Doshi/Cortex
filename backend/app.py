"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, FileResponse
from backend.history_manager import history_manager
from backend.report_generator import report_generator

from backend import __version__
from backend.agent import ask_agent
from backend.config import ensure_directories, setup_logging
from backend.dataset_manager import dataset_manager
from backend.models import (
    AnalysisRequest,
    AnalysisResponse,
    HealthResponse,
    ProfileRequest,
    ProfileResponse,
    UploadResponse,
)
from backend.profiler import profiler

logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Cortex",
    description="Autonomous Multi-Agent Data Investigation Platform",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Initialize runtime directories and logging."""
    setup_logging()
    ensure_directories()
    logger.info("Cortex backend started.")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="ok", service="Cortex", version=__version__)


@app.post(
    "/upload",
    response_model=UploadResponse,
    responses={400: {"description": "Invalid upload"}, 413: {"description": "File too large"}},
    tags=["datasets"],
)
async def upload_dataset(file: UploadFile = File(...)) -> UploadResponse:
    """Upload and validate a CSV dataset."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")

    content = await file.read()

    try:
        result = dataset_manager.save_upload(content, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[Upload] Failed to process uploaded CSV.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read CSV file: {exc}",
        ) from exc

    return UploadResponse(**result)


@app.post("/profile", response_model=ProfileResponse, tags=["datasets"])
def profile_dataset(request: ProfileRequest) -> ProfileResponse:
    """Compute a full statistical profile for a dataset."""
    try:
        profile = profiler.profile_file(request.file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[Profiling] Profile request failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profiling failed: {exc}",
        ) from exc

    return ProfileResponse(profile=profile)


@app.post("/analyze", response_model=AnalysisResponse, tags=["analysis"])
def analyze(request: AnalysisRequest) -> AnalysisResponse:
    """Analyze uploaded dataset(s) using the multi-agent pipeline."""
    file_paths = []
    if request.file_paths:
        file_paths = request.file_paths
    elif request.file_path:
        file_paths = [request.file_path]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one dataset file path must be provided via 'file_path' or 'file_paths'.",
        )

    try:
        import uuid
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        answer, plan, metrics = ask_agent(request.question, file_paths, execution_id=execution_id)
        
        # Validation for stale state leakages (Requirement 9)
        stale_words = ["department", "salary", "salaries", "engineering", "hr", "company"]
        is_titanic_or_unrelated = not any(w in request.question.lower() for w in ["salary", "department", "staff", "company", "employee"])
        if is_titanic_or_unrelated:
            text_to_check = answer.lower()
            for step in metrics.get("steps", []):
                if step.get("output"):
                    text_to_check += " " + str(step["output"]).lower()
            
            leakages = [word for word in stale_words if word in text_to_check]
            if leakages:
                logger.error("[Executor] Execution isolation error: stale state leakages detected: %s", leakages)
                raise HTTPException(
                    status_code=500,
                    detail=f"Execution isolation error: stale state leakage detected for words {leakages}"
                )
        
        # Save run in persistent history manager
        run_id = history_manager.save_run(
            question=request.question,
            datasets=file_paths,
            plan_dict=plan.model_dump(),
            metrics_dict=metrics,
            answer=answer
        )
        
        # Inject run ID in response metadata
        metadata = {"run_id": run_id, "execution_id": execution_id}
        
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[Analysis] Analysis request failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        ) from exc

    return AnalysisResponse(answer=answer, plan=plan, metrics=metrics, metadata=metadata)


@app.get("/history", tags=["history"])
def get_history():
    """List metadata for all past investigation runs."""
    try:
        return {"history": history_manager.list_runs()}
    except Exception as exc:
        logger.exception("[History] Failed to list investigation runs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load history: {exc}",
        ) from exc


@app.get("/history/{run_id}", tags=["history"])
def get_history_run(run_id: str):
    """Retrieve full details of a past investigation run."""
    run = history_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run


@app.get("/report/{run_id}", tags=["reports"])
def download_report(run_id: str):
    """Export and stream the PDF report download for a past run."""
    pdf_path = report_generator.generate_pdf(run_id)
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failed to generate report.")
    return FileResponse(
        path=pdf_path,
        filename=f"cortex_report_{run_id}.pdf",
        media_type="application/pdf"
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException) -> JSONResponse:
    """Return consistent JSON error payloads."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
