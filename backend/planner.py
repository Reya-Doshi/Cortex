"""Planner Agent — converts natural language requests into execution plans."""

from __future__ import annotations

import logging
from typing import Any

from backend.config import client, GEMINI_MODEL
from backend.dataset_manager import dataset_manager
from backend.models import ExecutionPlan, ToolStep
from google.genai import types

logger = logging.getLogger(__name__)


def find_semantic_column(cols: list[str], patterns: list[str]) -> str | None:
    """Perform case-insensitive check if any pattern matches a column name."""
    for col in cols:
        col_lower = col.lower()
        if any(pat in col_lower for pat in patterns):
            return col
    return None


def validate_intent_columns(question: str, col_names: list[str]) -> None:
    """Inspect query intent and ensure required columns are present in the dataset schema.
    
    If they do not exist, raise a planning error instead of substituting columns.
    """
    q_lower = question.lower()
    
    # 1. Age Group Survival
    if "age" in q_lower and any(w in q_lower for w in ["survive", "survival", "survived", "survivor"]):
        age_col = find_semantic_column(col_names, ["age", "passengerage", "ageyears"])
        survived_col = find_semantic_column(col_names, ["survived", "survival", "outcome", "survivor"])
        if not age_col or not survived_col:
            missing = []
            if not age_col: missing.append("Age")
            if not survived_col: missing.append("Survived")
            raise ValueError(f"Required columns {missing} for Age Group Survival analysis are missing from the dataset.")

    # 2. Survival by Sex
    elif any(w in q_lower for w in ["sex", "gender", "male", "female"]) and any(w in q_lower for w in ["survive", "survival", "survived", "survivor"]):
        sex_col = find_semantic_column(col_names, ["sex", "gender", "gender_code", "male", "female"])
        survived_col = find_semantic_column(col_names, ["survived", "survival", "outcome", "survivor"])
        if not sex_col or not survived_col:
            missing = []
            if not sex_col: missing.append("Sex/Gender")
            if not survived_col: missing.append("Survived")
            raise ValueError(f"Required columns {missing} for Survival by Sex analysis are missing from the dataset.")

    # 3. Average Salary by Department
    elif any(w in q_lower for w in ["salary", "salaries", "compensation"]) and any(w in q_lower for w in ["department", "dept", "division"]):
        salary_col = find_semantic_column(col_names, ["salary", "compensation", "pay", "salaries", "wage"])
        dept_col = find_semantic_column(col_names, ["dept", "department", "division", "team"])
        if not salary_col or not dept_col:
            missing = []
            if not salary_col: missing.append("Salary")
            if not dept_col: missing.append("Department")
            raise ValueError(f"Required columns {missing} for Average Salary by Department analysis are missing from the dataset.")

    # 4. Monthly Sales Trend
    elif "sales" in q_lower and any(w in q_lower for w in ["month", "monthly", "trend", "date"]):
        sales_col = find_semantic_column(col_names, ["sales", "revenue", "sales_amount", "turnover"])
        date_col = find_semantic_column(col_names, ["date", "month", "time", "order_date", "timestamp"])
        if not sales_col or not date_col:
            missing = []
            if not sales_col: missing.append("Sales")
            if not date_col: missing.append("Date/Month")
            raise ValueError(f"Required columns {missing} for Monthly Sales Trend analysis are missing from the dataset.")


class PlannerAgent:
    """Produces structured execution plans without directly answering questions."""

    def create_plan(self, question: str, file_paths: list[str], execution_id: str | None = None) -> ExecutionPlan:
        """Build a tool execution plan from the user's request using Gemini."""
        logger.info("[Planning] Creating plan for question: %s (execution: %s)", question, execution_id)
        
        # 1. Inspect current dataset schemas and validate intent column requirements
        schemas_info = []
        for path in file_paths:
            try:
                df = dataset_manager.load(path, execution_id=execution_id)
                col_names = list(df.columns)
                
                # Enforce strict column presence verification (Requirement 6)
                validate_intent_columns(question, col_names)
                
                dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
                schemas_info.append(
                    f"File: {path}\n"
                    f"Columns and Types: {dtypes}\n"
                    f"Row count: {len(df)}"
                )
            except ValueError as val_err:
                logger.error("[Planning] Column presence check failed: %s", val_err)
                raise
            except Exception as e:
                logger.warning("[Planning] Failed to inspect schema for %s: %s", path, e)
                schemas_info.append(f"File: {path} (Failed to load schema: {e})")

        schemas_str = "\n\n".join(schemas_info)

        prompt = f"""
You are the Planner Agent for the Cortex data investigation platform.
Your task is to analyze the user's request and the schema of the uploaded dataset(s) to generate a structured execution plan.

You must NEVER answer the user's question directly.
Your ONLY responsibility is to create the execution plan.

You must NEVER infer operations or columns from previous examples.
Analyze the current dataset schemas below and map user intent strictly:
- If required columns do not exist, do NOT replace them or substitute columns.

Datasets available:
{schemas_str}

User Question:
{question}

Available tools you can plan:
1. profile: Profile a dataset to understand its columns, metrics, quality, and preview.
2. execute_python: Execute Python code to aggregate, filter, merge, or compute statistics on the dataset.
   You must select a specific 'operation' parameter from:
   - groupby_age_bins: If the user requested age groups (e.g. survival by age group).
   - groupby_sex: If the user requested survival by sex/gender.
   - groupby_department_mean: If the user requested average salaries by department.
   - monthly_sales_trend: If monthly sales trend/amounts are requested.
   - sort_desc_limit: If sorting and limiting records (e.g. top 10 products) is requested.
   - correlation_matrix: If correlation analysis is requested.
   - histogram: If histogram/distribution of a column is requested.
   - missing_value_analysis: If missing value analysis is requested.
3. visualize: Generate a visualization (chart) from the processed data. Specify 'chart_type' ('bar', 'line', 'pie', 'histogram').
4. analyze: The final step. The Analysis Agent will interpret the findings.

For every planned ToolStep:
- You must populate the 'why' field explaining why this step and its operation were selected.
  Example: "I selected groupby_age_bins because the user requested age groups and the dataset contains Age and Survived columns."
- Ensure all paths lead to a final 'analyze' step.
"""

        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExecutionPlan,
                    system_instruction=(
                        "You are a strict data analysis planning agent. You never answer the question, "
                        "you only produce a structured JSON execution plan matching the schema. You always "
                        "explain why you selected each operation in the 'why' field."
                    ),
                    temperature=0.0,  # Keep it deterministic
                ),
            )

            if not response.text:
                raise ValueError("Planner Agent returned empty response.")

            plan = ExecutionPlan.model_validate_json(response.text)
            logger.info(
                "[Planning] Generated plan successfully | goal=%s | steps=%s",
                plan.goal,
                [f"{step.id}({step.tool}) | why: {step.why}" for step in plan.steps],
            )
            return plan

        except Exception as exc:
            if isinstance(exc, ValueError) and "Required columns" in str(exc):
                raise
            logger.exception("[Planning] Failed to generate execution plan.")
            fallback_steps = [
                ToolStep(
                    id="profile_fallback",
                    tool="profile",
                    dependencies=[],
                    description="Inspect dataset structure (fallback).",
                    why="Fallback profile step."
                ),
                ToolStep(
                    id="analyze_fallback",
                    tool="analyze",
                    dependencies=["profile_fallback"],
                    description="Perform final analysis (fallback).",
                    why="Fallback analyze step.",
                    question=question
                )
            ]
            return ExecutionPlan(
                goal=f"Execute analysis for: {question}",
                reasoning="Fallback plan due to error.",
                confidence=0.5,
                steps=fallback_steps,
                expected_outputs="Dataset profile and final text analysis."
            )


planner = PlannerAgent()
