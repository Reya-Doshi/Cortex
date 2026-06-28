"""History Manager — saves and loads completed investigation runs as JSON files."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import OUTPUTS_DIR

logger = logging.getLogger(__name__)

HISTORY_DIR = OUTPUTS_DIR / "history"


class HistoryManager:
    """Manages local JSON persistence for past data investigations."""

    def __init__(self) -> None:
        self.ensure_history_dir()

    @staticmethod
    def ensure_history_dir() -> None:
        """Create the history folder inside outputs/ if it doesn't exist."""
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    def save_run(
        self,
        question: str,
        datasets: list[str],
        plan_dict: dict[str, Any],
        metrics_dict: dict[str, Any],
        answer: str,
    ) -> str:
        """Serialize and save an investigation run."""
        self.ensure_history_dir()
        
        run_id = uuid.uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        
        payload = {
            "id": run_id,
            "timestamp": timestamp,
            "question": question,
            "datasets": datasets,
            "plan": plan_dict,
            "metrics": metrics_dict,
            "answer": answer,
        }
        
        destination = HISTORY_DIR / f"{run_id}.json"
        
        try:
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            logger.info("[History] Saved investigation run: %s", run_id)
            return run_id
        except Exception as e:
            logger.exception("[History] Failed to save investigation: %s", e)
            return ""

    def list_runs(self) -> list[dict[str, Any]]:
        """List summary metadata for all completed runs, ordered newest first."""
        self.ensure_history_dir()
        runs = []
        
        for file_path in HISTORY_DIR.glob("*.json"):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                runs.append({
                    "id": data.get("id"),
                    "timestamp": data.get("timestamp"),
                    "question": data.get("question"),
                    "datasets": data.get("datasets"),
                    "steps_count": len(data.get("plan", {}).get("steps", [])),
                    "total_duration_ms": data.get("metrics", {}).get("total_duration_ms", 0.0),
                    "confidence": data.get("plan", {}).get("confidence", 1.0),
                })
            except Exception as e:
                logger.warning("[History] Failed to read run file %s: %s", file_path.name, e)

        # Sort descending by timestamp
        runs.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return runs

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Load and return the complete payload for a specific run ID."""
        file_path = HISTORY_DIR / f"{run_id}.json"
        if not file_path.exists():
            logger.warning("[History] Requested run ID %s not found.", run_id)
            return None
        
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.exception("[History] Failed to load run %s", run_id)
            return None


history_manager = HistoryManager()
