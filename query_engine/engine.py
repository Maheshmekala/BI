"""
Core engine: takes natural language questions + datasets and returns
structured results with data, visualizations, and recommendations.
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd

from data_sources.base import Dataset
from llm import LLMProvider, LLMMessage, SYSTEM_PROMPTS, get_llm


@dataclass
class ChartRecommendation:
    chart_type: str  # "bar", "line", "scatter", "pie", "area", "heatmap", "histogram"
    title: str
    x_column: str
    y_column: str | list[str]
    aggregation: str = "none"  # "sum", "mean", "count", "none"
    color_column: str | None = None
    description: str = ""


@dataclass
class QueryResult:
    answer: str = ""
    data: pd.DataFrame | None = None
    charts: list[ChartRecommendation] = field(default_factory=list)
    sql_query: str | None = None
    code_snippet: str | None = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "charts": [c.__dict__ for c in self.charts],
            "sql_query": self.sql_query,
            "code_snippet": self.code_snippet,
            "error": self.error,
            "metadata": self.metadata,
        }


class QueryEngine:
    """Main query engine — turns natural language into data insights."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or get_llm()
        self._history: list[dict] = []

    def _build_dataset_context(self, dataset: Dataset) -> str:
        """Build a rich textual description of a dataset for the LLM prompt."""
        summary = dataset.summary()
        lines = []
        lines.append(f"Dataset: {dataset.name}")
        lines.append(f"Rows: {summary['rows']} | Columns: {summary['columns']}")
        lines.append(f"\nColumns: {', '.join(summary['column_names'])}")
        lines.append(f"Numeric: {summary['numeric_columns']}")
        lines.append(f"Categorical: {summary['categorical_columns']}")
        lines.append(f"Dates: {summary['date_columns']}")

        # Missing data
        missing = [f"{k}({v})" for k, v in summary["missing_data"].items() if v > 0]
        if missing:
            lines.append(f"\nMissing values: {', '.join(missing)}")

        # Sample rows
        lines.append("\n--- Sample Data (first 10 rows) ---")
        lines.append(json.dumps(summary["sample"], indent=2, default=str)[:3000])

        # Basic stats
        if summary.get("basic_stats"):
            lines.append("\n--- Summary Statistics ---")
            lines.append(json.dumps(summary["basic_stats"], indent=2, default=str)[:2000])

        return "\n".join(lines)

    def _parse_chart_recommendations(self, text: str) -> list[ChartRecommendation]:
        """Extract chart recommendations from LLM response text."""
        charts = []

        # Try to find JSON block with chart specs
        json_pattern = r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```"
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict):
                    items = [data]
                else:
                    items = data
                for item in items:
                    if isinstance(item, dict) and "chart_type" in item:
                        charts.append(ChartRecommendation(
                            chart_type=item["chart_type"],
                            title=item.get("title", ""),
                            x_column=item.get("x_column", item.get("x", "")),
                            y_column=item.get("y_column", item.get("y", "")),
                            aggregation=item.get("aggregation", "none"),
                            color_column=item.get("color_column"),
                            description=item.get("description", item.get("desc", "")),
                        ))
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: parse structured chart hints in text
        chart_hints = re.findall(
            r"(?:chart|plot|graph|visualization)[:\s]+(\w+(?:\s+\w+)*)\s*[:\-]\s*x[:\s]*(\w+)\s*[,\s]+y[:\s]*(\w+)",
            text, re.IGNORECASE,
        )
        for hint in chart_hints:
            charts.append(ChartRecommendation(
                chart_type="bar" if hint[0].lower() in ("bar", "column") else "line" if "line" in hint[0].lower() else "bar",
                title=hint[0].strip(),
                x_column=hint[1].strip(),
                y_column=hint[2].strip(),
            ))

        return charts

    def _execute_pandas(self, code: str, df: pd.DataFrame) -> str:
        """Safely execute a pandas code snippet and return the result string."""
        try:
            local_vars = {"df": df, "pd": pd}
            exec(code, {"__builtins__": {}}, local_vars)
            result = local_vars.get("result", local_vars.get("_", ""))
            return str(result)
        except Exception as exc:
            return f"Execution error: {exc}"

    def query(
        self,
        question: str,
        dataset: Dataset | None = None,
        context: str = "",
        system_prompt_key: str = "data_analyst",
        generate_charts: bool = True,
    ) -> QueryResult:
        """Answer a natural language question against a dataset."""
        result = QueryResult()

        try:
            # Build system prompt
            system = SYSTEM_PROMPTS.get(system_prompt_key, SYSTEM_PROMPTS["data_analyst"])

            # Build user prompt with dataset context
            user_parts = []
            if dataset:
                user_parts.append(self._build_dataset_context(dataset))
            if context:
                user_parts.append(f"Additional context: {context}")
            user_parts.append(f"User question: {question}")

            if generate_charts:
                user_parts.append(
                    "\n\nAfter your analysis, if appropriate, provide chart recommendations "
                    "in a JSON code block. Each chart should have: chart_type, title, x_column, "
                    "y_column (can be a list), aggregation (sum/mean/count/none), description."
                    "Example: ```json\n{\"chart_type\": \"bar\", \"title\": \"Sales by Region\", "
                    "\"x_column\": \"region\", \"y_column\": \"sales\", \"aggregation\": \"sum\"}\n```"
                )

            user_prompt = "\n\n".join(user_parts)

            messages = [
                LLMMessage(role="system", content=system),
                LLMMessage(role="user", content=user_prompt),
            ]

            # Get LLM response
            response = self.llm.chat(messages)
            result.answer = response.content
            result.metadata = {
                "model": response.model,
                "provider": response.provider,
                "latency_ms": response.latency_ms,
                "usage": response.usage,
            }

            # Extract chart recommendations
            if generate_charts:
                result.charts = self._parse_chart_recommendations(response.content)

        except Exception as exc:
            result.error = str(exc)
            result.answer = f"I encountered an error processing your question: {exc}"

        # Record history
        self._history.append({
            "question": question,
            "dataset": dataset.name if dataset else None,
            "result": result.to_dict(),
        })

        return result

    def generate_sql(
        self,
        question: str,
        schema: dict[str, list[dict]],
        dialect: str = "postgresql",
    ) -> str:
        """Generate a SQL query from natural language."""
        system = SYSTEM_PROMPTS["sql_generator"]
        schema_str = json.dumps(schema, indent=2)
        prompt = (
            f"Database schema:\n{schema_str}\n\n"
            f"SQL dialect: {dialect}\n\n"
            f"Question: {question}\n\n"
            f"Generate ONLY the SQL query in a ```sql block."
        )
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=prompt),
        ]
        response = self.llm.chat(messages)
        # Extract SQL from code block
        sql_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", response.content, re.DOTALL)
        return sql_match.group(1).strip() if sql_match else response.content.strip()

    def get_history(self) -> list[dict]:
        return self._history

    def clear_history(self) -> None:
        self._history = []
