import pytest
import os
import pandas as pd
from unittest.mock import patch
from backend.planner import planner

class MockResponse:
    def __init__(self, text):
        self.text = text

def mock_generate_content(model, contents, config=None):
    prompt_lower = contents.lower()
    
    # Extract only the user's question from the prompt by splitting between delimiters
    if "user question:" in prompt_lower:
        part = prompt_lower.split("user question:")[1]
        if "available tools" in part:
            q_lower = part.split("available tools")[0]
        else:
            q_lower = part
    else:
        q_lower = prompt_lower

    op = "groupby_sex"
    why_msg = "Sex column survival rate analysis."
    chart_t = "bar"
    
    if "age group" in q_lower or "age bins" in q_lower or ("age" in q_lower and "survive" in q_lower):
        op = "groupby_age_bins"
        why_msg = "I selected groupby_age_bins because the user requested age groups and the dataset contains Age and Survived columns."
    elif "sex" in q_lower or "gender" in q_lower:
        op = "groupby_sex"
        why_msg = "I selected groupby_sex because the user requested survival by sex and gender."
    elif "salary" in q_lower or "department" in q_lower:
        op = "groupby_department_mean"
        why_msg = "Department-wise average salaries."
    elif "sales" in q_lower:
        op = "monthly_sales_trend"
        why_msg = "Monthly sales trends."
        chart_t = "line"
    elif "missing" in q_lower:
        op = "missing_value_analysis"
        why_msg = "Null value counts."
    elif "hist" in q_lower:
        op = "histogram"
        why_msg = "Frequency distribution."
        chart_t = "histogram"
    elif "corr" in q_lower:
        op = "correlation_matrix"
        why_msg = "Numeric columns correlation."
        chart_t = "heatmap"

    mock_json = f"""{{
      "goal": "Test goal",
      "reasoning": "Test reasoning",
      "confidence": 0.95,
      "steps": [
        {{
          "id": "profile_1",
          "tool": "profile",
          "dependencies": [],
          "description": "Profile dataset",
          "why": "I selected profile for initial schemas."
        }},
        {{
          "id": "exec_python_1",
          "tool": "execute_python",
          "dependencies": ["profile_1"],
          "description": "Analyze dataset",
          "operation": "{op}",
          "why": "{why_msg}"
        }},
        {{
          "id": "visualize_1",
          "tool": "visualize",
          "dependencies": ["exec_python_1"],
          "description": "Render chart",
          "chart_type": "{chart_t}",
          "why": "Render visualization."
        }},
        {{
          "id": "analyze_1",
          "tool": "analyze",
          "dependencies": ["visualize_1"],
          "description": "Final explanation",
          "why": "Analyze results."
        }}
      ],
      "expected_outputs": "Test outputs"
    }}"""
    return MockResponse(mock_json)

@pytest.fixture(autouse=True)
def mock_gemini():
    """Automatically patch client.models.generate_content with mock response."""
    with patch("backend.planner.client.models.generate_content", side_effect=mock_generate_content) as mock:
        yield mock

@pytest.fixture
def temp_csv_factory(tmp_path):
    """Fixture to generate temporary CSV datasets for tests."""
    def _create_csv(filename, data):
        filepath = tmp_path / filename
        pd.DataFrame(data).to_csv(filepath, index=False)
        return str(filepath)
    return _create_csv

def test_age_group_survival(temp_csv_factory):
    filepath = temp_csv_factory(
        "titanic_mock.csv",
        {
            "PassengerAge": [22, 38, 26, 35, 54],
            "OutCome": [0, 1, 1, 1, 0],
            "Name": ["A", "B", "C", "D", "E"]
        }
    )
    
    question = "Which age group survived the most?"
    plan = planner.create_plan(question, [filepath], execution_id="test_age")
    
    exec_step = next((s for s in plan.steps if s.tool in ["execute_python", "python_analysis"]), None)
    
    assert exec_step is not None
    assert exec_step.operation == "groupby_age_bins"
    assert exec_step.why is not None
    assert "age" in exec_step.why.lower() or "survived" in exec_step.why.lower()

def test_survival_by_sex(temp_csv_factory):
    filepath = temp_csv_factory(
        "titanic_mock2.csv",
        {
            "Sex": ["male", "female", "female", "female", "male"],
            "Survived": [0, 1, 1, 1, 0]
        }
    )
    
    question = "What is the survival by sex?"
    plan = planner.create_plan(question, [filepath], execution_id="test_sex")
    
    exec_step = next((s for s in plan.steps if s.tool in ["execute_python", "python_analysis"]), None)
    
    assert exec_step is not None
    assert exec_step.operation == "groupby_sex"
    assert exec_step.why is not None

def test_average_salary_by_department(temp_csv_factory):
    filepath = temp_csv_factory(
        "company_mock.csv",
        {
            "division": ["HR", "Engineering", "Marketing"],
            "Pay": [50000, 95000, 70000]
        }
    )
    
    question = "What is the average salary by department?"
    plan = planner.create_plan(question, [filepath], execution_id="test_salary")
    
    exec_step = next((s for s in plan.steps if s.tool in ["execute_python", "python_analysis"]), None)
    
    assert exec_step is not None
    assert exec_step.operation == "groupby_department_mean"
    assert exec_step.why is not None

def test_monthly_sales_trend(temp_csv_factory):
    filepath = temp_csv_factory(
        "sales_mock.csv",
        {
            "order_date": ["2026-01-01", "2026-02-01", "2026-03-01"],
            "sales_amount": [100.50, 250.00, 180.20]
        }
    )
    
    question = "Show the monthly sales trend."
    plan = planner.create_plan(question, [filepath], execution_id="test_sales")
    
    exec_step = next((s for s in plan.steps if s.tool in ["execute_python", "python_analysis"]), None)
    
    assert exec_step is not None
    assert exec_step.operation == "monthly_sales_trend"

def test_missing_value_analysis(temp_csv_factory):
    filepath = temp_csv_factory(
        "missing_mock.csv",
        {"col1": [1, None, 3]}
    )
    
    question = "Show missing value analysis."
    plan = planner.create_plan(question, [filepath], execution_id="test_missing")
    
    exec_step = next((s for s in plan.steps if s.tool in ["execute_python", "python_analysis"]), None)
    
    assert exec_step is not None
    assert exec_step.operation == "missing_value_analysis"

def test_histogram_generation(temp_csv_factory):
    filepath = temp_csv_factory(
        "hist_mock.csv",
        {"Age": [22, 38, 26, 35, 54]}
    )
    
    question = "Generate a histogram of age distribution."
    plan = planner.create_plan(question, [filepath], execution_id="test_hist")
    
    exec_step = next((s for s in plan.steps if s.tool in ["execute_python", "python_analysis"]), None)
    
    assert exec_step is not None
    assert exec_step.operation == "histogram"

def test_correlation_analysis(temp_csv_factory):
    filepath = temp_csv_factory(
        "corr_mock.csv",
        {
            "Age": [22, 38, 26, 35, 54],
            "Fare": [7.25, 71.28, 7.92, 53.1, 51.86]
        }
    )
    
    question = "Show correlation analysis between age and fare."
    plan = planner.create_plan(question, [filepath], execution_id="test_corr")
    
    exec_step = next((s for s in plan.steps if s.tool in ["execute_python", "python_analysis"]), None)
    
    assert exec_step is not None
    assert exec_step.operation == "correlation_matrix"

def test_missing_columns_error(temp_csv_factory):
    filepath = temp_csv_factory(
        "invalid_mock.csv",
        {
            "Sex": ["male", "female"],
            "Survived": [0, 1]
        }
    )
    
    question = "Which age group survived the most?"
    
    with pytest.raises(ValueError) as excinfo:
        planner.create_plan(question, [filepath], execution_id="test_missing_err")
        
    assert "Required columns" in str(excinfo.value)
    assert "Age" in str(excinfo.value)
