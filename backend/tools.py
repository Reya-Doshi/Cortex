"""Tool registry — callable tools used by the Tool Executor."""

from __future__ import annotations

import logging
from typing import Any, Callable
import pandas as pd

from backend.models import DatasetProfile
from backend.profiler import profiler
from backend.visualizer import visualizer
from backend.dataset_manager import dataset_manager
from backend.planner import find_semantic_column

logger = logging.getLogger(__name__)

ToolCallable = Callable[..., dict[str, Any]]


def tool_profile(file_path: str, execution_id: str | None = None, **_kwargs: Any) -> dict[str, Any]:
    """Profile a dataset and return structured statistics."""
    profile = profiler.profile_file(file_path, execution_id=execution_id)
    return {"profile": profile.model_dump()}


def tool_visualize(dependency_outputs: dict[str, Any] | None = None, chart_type: str = "bar", execution_id: str | None = None, **_kwargs: Any) -> dict[str, Any]:
    """Generate visualizer output from processed datasets only (never raw CSV)."""
    processed_data = None
    if dependency_outputs:
        for dep_id, output in reversed(list(dependency_outputs.items())):
            if "data" in output or "profile" in output:
                processed_data = output
                break

    return visualizer.generate(processed_data=processed_data, chart_type=chart_type)


def tool_execute_python(file_path: str, execution_id: str | None = None, dependency_outputs: dict[str, Any] | None = None, operation: str = "", **_kwargs: Any) -> dict[str, Any]:
    """Execute dynamic analysis aggregation on dataset. Isolated by execution_id."""
    logger.info("[Execution] execute_python tool invoked for file: %s, operation: %s, execution: %s", file_path, operation, execution_id)
    
    df = dataset_manager.load(file_path, execution_id=execution_id)
    cols = list(df.columns)
    
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=["number"]).columns.tolist()
    
    # Exclude any index-like numeric column if possible
    num_cols = [c for c in num_cols if "id" not in c.lower() and c != "index" and c.lower() != "passengerid"]
    
    data_list = []
    columns = []

    # 1. Age Group Survival
    if operation == "groupby_age_bins":
        age_col = find_semantic_column(cols, ["age", "passengerage", "ageyears"])
        survived_col = find_semantic_column(cols, ["survived", "survival", "outcome", "survivor"])
        
        a_col = age_col or (num_cols[0] if num_cols else cols[0])
        s_col = survived_col or (num_cols[1] if len(num_cols) > 1 else cols[0])
        
        # Create bins
        df["age_group"] = pd.cut(
            df[a_col].dropna(),
            bins=[0, 12, 18, 35, 60, 100],
            labels=["Child", "Teen", "Young Adult", "Adult", "Senior"]
        )
        grouped = df.groupby("age_group", observed=False)[s_col].mean().reset_index()
        grouped[s_col] = grouped[s_col].round(2)
        grouped.columns = ["age_group", "survival_rate"]
        
        data_list = grouped.to_dict(orient="records")
        columns = ["age_group", "survival_rate"]

    # 2. Survival by Sex
    elif operation == "groupby_sex":
        sex_col = find_semantic_column(cols, ["sex", "gender", "gender_code", "male", "female"])
        survived_col = find_semantic_column(cols, ["survived", "survival", "outcome", "survivor"])
        
        g_col = sex_col or (cat_cols[0] if cat_cols else cols[0])
        s_col = survived_col or (num_cols[0] if num_cols else cols[0])
        
        grouped = df.groupby(g_col)[s_col].mean().reset_index()
        grouped[s_col] = grouped[s_col].round(2)
        grouped.columns = ["gender", "survival_rate"]
        
        data_list = grouped.to_dict(orient="records")
        columns = ["gender", "survival_rate"]

    # 3. Average Salary by Department
    elif operation == "groupby_department_mean":
        salary_col = find_semantic_column(cols, ["salary", "compensation", "pay", "salaries", "wage"])
        dept_col = find_semantic_column(cols, ["dept", "department", "division", "team"])
        
        s_col = salary_col or (num_cols[0] if num_cols else cols[0])
        d_col = dept_col or (cat_cols[0] if cat_cols else cols[0])
        
        grouped = df.groupby(d_col)[s_col].mean().reset_index()
        grouped[s_col] = grouped[s_col].round(2)
        grouped.columns = ["department", "average_salary"]
        
        data_list = grouped.to_dict(orient="records")
        columns = ["department", "average_salary"]

    # 4. Monthly Sales Trend
    elif operation == "monthly_sales_trend":
        sales_col = find_semantic_column(cols, ["sales", "revenue", "sales_amount", "turnover"])
        date_col = find_semantic_column(cols, ["date", "month", "time", "order_date", "timestamp"])
        
        sl_col = sales_col or (num_cols[0] if num_cols else cols[0])
        dt_col = date_col or cols[0]
        
        df["parsed_date"] = pd.to_datetime(df[dt_col], errors="coerce")
        df["month"] = df["parsed_date"].dt.strftime("%b")
        
        grouped = df.groupby("month")[sl_col].sum().reset_index()
        grouped[sl_col] = grouped[sl_col].round(2)
        grouped.columns = ["month", "total_sales"]
        
        # Sort months chronologically if possible
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        grouped["month"] = pd.Categorical(grouped["month"], categories=month_order, ordered=True)
        grouped = grouped.sort_values("month").reset_index(drop=True)
        grouped["month"] = grouped["month"].astype(str)
        
        data_list = grouped.to_dict(orient="records")
        columns = ["month", "total_sales"]

    # 5. Top 10 Descending
    elif operation == "sort_desc_limit":
        metric_col = num_cols[0] if num_cols else cols[0]
        df_sorted = df.sort_values(by=metric_col, ascending=False).head(10)
        data_list = df_sorted.to_dict(orient="records")
        columns = list(df_sorted.columns)

    # 6. Correlation Analysis
    elif operation == "correlation_matrix":
        if len(num_cols) >= 2:
            corr = df[num_cols].corr().round(2).reset_index()
            data_list = corr.to_dict(orient="records")
            columns = list(corr.columns)
        else:
            data_list = [{"metric": "Not enough numeric columns", "value": 0}]
            columns = ["metric", "value"]

    # 7. Histogram Generation
    elif operation == "histogram":
        h_col = num_cols[0] if num_cols else cols[0]
        df["range"] = pd.cut(df[h_col].dropna(), bins=5).astype(str)
        grouped = df["range"].value_counts().reset_index()
        grouped.columns = ["range", "frequency"]
        data_list = grouped.to_dict(orient="records")
        columns = ["range", "frequency"]

    # 8. Missing Value Analysis
    elif operation == "missing_value_analysis":
        nulls = df.isnull().sum().reset_index()
        nulls.columns = ["column", "missing_count"]
        data_list = nulls.to_dict(orient="records")
        columns = ["column", "missing_count"]

    # Default fallback groupby (dynamic)
    elif cat_cols and num_cols:
        cat_col = cat_cols[0]
        num_col = num_cols[0]
        grouped = df.groupby(cat_col)[num_col].mean().reset_index()
        if grouped[num_col].dtype.kind in "fc":
            grouped[num_col] = grouped[num_col].round(2)
        data_list = grouped.to_dict(orient="records")
        columns = [cat_col, num_col]
    else:
        # Fallback to head
        data_list = df.head(5).to_dict(orient="records")
        columns = list(df.columns)

    return {
        "status": "success",
        "operation": operation,
        "message": f"Aggregation completed dynamically for {file_path}",
        "columns": columns,
        "data": data_list
    }


def tool_analyze(dependency_outputs: dict[str, Any] | None = None, question: str = "", execution_id: str | None = None, **_kwargs: Any) -> dict[str, Any]:
    """Prepare context from tool outputs for final explanation."""
    return {
        "question": question,
        "dependency_outputs": dependency_outputs or {},
    }


TOOL_REGISTRY: dict[str, ToolCallable] = {
    "profile": tool_profile,
    "analyze": tool_analyze,
    "visualize": tool_visualize,
    "execute_python": tool_execute_python,
    "python_analysis": tool_execute_python,
}


def build_context_from_profile(profile: DatasetProfile) -> str:
    """Format a dataset profile as text context for the Analysis Agent."""
    missing = profile.missing_values
    return f"""
Dataset Profile

Rows: {profile.rows}
Columns: {profile.column_names}
Data Types: {profile.dtypes}
Missing Values: {missing}
Duplicate Rows: {profile.duplicate_rows}
Numeric Summary: {profile.numeric_summary}

Preview (first 5 rows):
{profile.preview}
"""
