"""Auto-insights, KPI identification, and statistical analysis engine."""

from __future__ import annotations
from typing import Any, Optional
import json
import re

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

from data_sources.base import Dataset
from llm import LLMMessage, SYSTEM_PROMPTS, get_llm, LLMProvider


class InsightsEngine:
    """Statistical + LLM-powered insights engine."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or get_llm()

    def analyze(self, dataset: Dataset) -> dict[str, Any]:
        """Run a full analysis pipeline on a dataset."""
        return {
            "overview": self._overview(dataset),
            "statistical": self._statistical_analysis(dataset.df),
            "correlations": self._correlation_analysis(dataset.df),
            "outliers": self._find_outliers(dataset.df),
            "trends": self._detect_trends(dataset.df),
            "kpis": self._identify_kpis(dataset),
            "llm_insights": self._llm_insights(dataset),
        }

    def _overview(self, dataset: Dataset) -> dict:
        df = dataset.df
        return {
            "name": dataset.name,
            "rows": len(df),
            "columns": len(df.columns),
            "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB",
            "duplicate_rows": int(df.duplicated().sum()),
            "completeness": round((1 - df.isna().sum().sum() / (df.shape[0] * df.shape[1])) * 100, 1),
        }

    def _statistical_analysis(self, df: pd.DataFrame) -> dict:
        """Compute advanced statistics for numeric columns."""
        numeric = df.select_dtypes(include=[np.number])
        if numeric.empty:
            return {"message": "No numeric columns found."}

        stats = {}
        for col in numeric.columns:
            col_data = numeric[col].dropna()
            if len(col_data) < 2:
                continue
            try:
                skew = scipy_stats.skew(col_data)
                kurt = scipy_stats.kurtosis(col_data)
                # Normality test (only for smaller datasets)
                normality = None
                if len(col_data) < 5000:
                    _, p_val = scipy_stats.normaltest(col_data)
                    normality = "normal" if p_val > 0.05 else "non-normal"

                stats[col] = {
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "mean": float(col_data.mean()),
                    "median": float(col_data.median()),
                    "std": float(col_data.std()),
                    "skewness": float(skew),
                    "kurtosis": float(kurt),
                    "q1": float(col_data.quantile(0.25)),
                    "q3": float(col_data.quantile(0.75)),
                    "iqr": float(col_data.quantile(0.75) - col_data.quantile(0.25)),
                    "distribution": normality,
                }
            except Exception:
                continue
        return stats

    def _correlation_analysis(self, df: pd.DataFrame) -> dict:
        """Find significant correlations."""
        numeric = df.select_dtypes(include=[np.number])
        if numeric.shape[1] < 2:
            return {"message": "Need at least 2 numeric columns for correlation."}

        corr = numeric.corr(method="pearson")
        significant = []

        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) >= 0.3:
                    significant.append({
                        "col1": corr.columns[i],
                        "col2": corr.columns[j],
                        "correlation": round(val, 3),
                        "strength": "strong" if abs(val) >= 0.7 else "moderate" if abs(val) >= 0.5 else "weak",
                        "direction": "positive" if val > 0 else "negative",
                    })

        significant.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return {
            "matrix": corr.round(3).to_dict(),
            "significant_pairs": significant[:20],
        }

    def _find_outliers(self, df: pd.DataFrame) -> dict:
        """Detect outliers using IQR method."""
        numeric = df.select_dtypes(include=[np.number])
        outliers = {}

        for col in numeric.columns:
            col_data = numeric[col].dropna()
            if len(col_data) < 4:
                continue
            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_mask = (col_data < lower) | (col_data > upper)
            n_outliers = outlier_mask.sum()
            if n_outliers > 0 and n_outliers / len(col_data) < 0.2:
                outliers[col] = {
                    "count": int(n_outliers),
                    "percentage": round(float(n_outliers / len(col_data) * 100), 1),
                    "lower_bound": float(lower),
                    "upper_bound": float(upper),
                    "outlier_values": col_data[outlier_mask].head(10).tolist(),
                }
        return outliers

    def _detect_trends(self, df: pd.DataFrame) -> list[dict]:
        """Simple trend analysis on numeric columns over row index."""
        numeric = df.select_dtypes(include=[np.number])
        trends = []
        for col in numeric.columns[:10]:
            col_data = numeric[col].dropna()
            if len(col_data) < 5:
                continue
            try:
                slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(
                    range(len(col_data)), col_data.values
                )
                if abs(slope) > 0.01:
                    trends.append({
                        "column": col,
                        "trend": "upward" if slope > 0 else "downward",
                        "slope": round(float(slope), 4),
                        "r_squared": round(float(r_value ** 2), 3),
                        "p_value": round(float(p_value), 4),
                        "significant": bool(p_value < 0.05),
                    })
            except Exception:
                continue
        return sorted(trends, key=lambda x: abs(x["slope"]), reverse=True)

    def _identify_kpis(self, dataset: Dataset) -> list[dict]:
        """Automatically identify KPIs from the dataset."""
        df = dataset.df
        numeric = df.select_dtypes(include=[np.number])
        kpis = []

        for col in numeric.columns[:10]:
            col_data = numeric[col].dropna()
            if len(col_data) < 2:
                continue
            try:
                current = float(col_data.iloc[-1])
                previous = float(col_data.iloc[0])
                change = ((current - previous) / previous * 100) if previous != 0 else 0
            except Exception:
                current = float(col_data.mean())
                change = 0

            direction = "up" if change > 0 else "down"
            is_good = direction == "up"  # Heuristic; user can override

            kpis.append({
                "label": col.replace("_", " ").title(),
                "value": f"{current:,.2f}" if abs(current) < 1e6 else f"{current:,.0f}",
                "delta": f"{change:+.1f}%",
                "direction": direction,
                "is_good": is_good,
                "icon": "📈" if is_good else "📉",
                "column": col,
                "aggregation": "last_value",
            })

        # Also add row count as a KPI
        kpis.insert(0, {
            "label": "Total Records",
            "value": f"{len(df):,}",
            "delta": f"{len(df.columns)} columns",
            "direction": "neutral",
            "is_good": True,
            "icon": "📊",
            "aggregation": "count",
        })

        return kpis

    def _llm_insights(self, dataset: Dataset) -> str:
        """Use LLM to generate narrative insights."""
        summary = dataset.summary()
        summary_str = json.dumps(summary, indent=2, default=str)[:3000]

        prompt = (
            f"Analyze this dataset and provide 5-7 key business insights:\n\n"
            f"Dataset: {dataset.name}\n"
            f"Rows: {summary['rows']}, Columns: {summary['columns']}\n"
            f"Numeric: {summary['numeric_columns']}\n"
            f"Categorical: {summary['categorical_columns']}\n"
            f"Missing data: {summary['missing_data']}\n\n"
            f"Full summary:\n{summary_str}\n\n"
            "For each insight include: what was found, why it matters, and a recommended action."
        )

        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPTS["insight_generator"]),
            LLMMessage(role="user", content=prompt),
        ]

        try:
            response = self.llm.chat(messages)
            return response.content
        except Exception as exc:
            return f"Could not generate LLM insights: {exc}"
