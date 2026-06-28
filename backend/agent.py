"""Analysis Agent — interprets tool outputs and produces explanations."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from backend.config import GEMINI_MODEL, client
from backend.models import DatasetProfile, ExecutionPlan, ExecutionResult
from backend.planner import planner
from backend.executor import executor
from backend.tools import build_context_from_profile

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """Interprets execution results and generates natural-language answers."""

    def explain(
        self,
        question: str,
        execution: ExecutionResult,
    ) -> str:
        """Produce a natural-language answer from tool execution outputs."""
        logger.info("[Analysis] Generating explanation for: %s", question)

        profile_data = self._extract_profile(execution)
        if profile_data is None:
            context = "No dataset profile details available."
        else:
            context = build_context_from_profile(profile_data)

        # Collect tool outputs by step ID
        tool_outputs = {}
        for result in execution.results:
            if result.success:
                tool_outputs[result.step_id] = {
                    "tool": result.tool,
                    "output": result.output
                }
            else:
                tool_outputs[result.step_id] = {
                    "tool": result.tool,
                    "error": result.error
                }

        prompt = f"""
You are a data analyst assistant for the Cortex platform.
Your job is to explain the analysis findings and business insights to the user.

Below is the structured data we gathered from executing our planned tools:

Dataset Schema Info:
{context}

Tool Outputs:
{tool_outputs}

User Question:
{question}

Based ONLY on the dataset profile and the tool outputs, provide a clear, professional, and comprehensive answer.
Be concise but thorough. Focus on business insights and clear answers to the user's question.
If a visualization step was run, mention it and explain what trends it shows in the outputs.
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        answer = response.text or "No response generated."
        logger.info("[Analysis] Explanation generated (%d chars)", len(answer))
        return answer

    @staticmethod
    def _extract_profile(execution: ExecutionResult) -> DatasetProfile | None:
        """Pull the dataset profile from execution results, if present."""
        for result in execution.results:
            if result.tool == "profile" and result.success:
                profile_dict = result.output.get("profile")
                if profile_dict:
                    return DatasetProfile(**profile_dict)
        return None


analysis_agent = AnalysisAgent()


def ask_agent(question: str, file_paths: list[str], execution_id: str | None = None) -> tuple[str, ExecutionPlan, dict[str, Any]]:
    """Orchestrate the multi-agent pipeline: plan → execute → explain."""
    if not execution_id:
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
    # 1. Plan
    plan = planner.create_plan(question, file_paths, execution_id=execution_id)
    
    # Set default file path for backward compatibility
    plan_file_path = file_paths[0] if file_paths else ""
    # Record metadata file path for executor compatibility
    object.__setattr__(plan, "file_path", plan_file_path)
    object.__setattr__(plan, "execution_id", execution_id)
    
    # 2. Execute
    execution = executor.execute(plan, execution_id=execution_id)

    # 3. Explain
    answer = analysis_agent.explain(question, execution)
    
    # 4. Construct execution metrics
    metrics = {
        "total_duration_ms": execution.total_duration_ms,
        "steps": [
            {
                "step_id": r.step_id,
                "tool": r.tool,
                "success": r.success,
                "start_time": r.start_time,
                "end_time": r.end_time,
                "duration_ms": r.duration_ms,
                "error": r.error,
                "output": r.output
            }
            for r in execution.results
        ]
    }
    
    return answer, plan, metrics
