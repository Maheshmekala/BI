"""Dynamic visualization engine — renders Plotly charts from recommendations."""

from __future__ import annotations
from typing import Any, Optional
import io
import base64

import matplotlib
matplotlib.use("Agg")  # must be set before importing pyplot

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt

from query_engine.engine import ChartRecommendation


# ── Plotly chart builder ──

def render_chart(
    chart: ChartRecommendation,
    df: pd.DataFrame,
    width: int = 600,
    height: int = 400,
) -> go.Figure:
    """Render a single chart recommendation against the dataframe."""
    chart_type = chart.chart_type.lower()
    x = chart.x_column
    y = chart.y_column
    color = chart.color_column
    agg = chart.aggregation

    # Validate columns exist
    if x and x not in df.columns:
        x = None
    if isinstance(y, str):
        if y not in df.columns:
            y = None
    elif isinstance(y, list):
        y = [c for c in y if c in df.columns]
        if not y:
            y = None
        else:
            y = y[0]  # Use first valid for simple charts
    if color and color not in df.columns:
        color = None

    # Apply aggregation
    if agg != "none" and x and y and df[x].dtype == "object":
        try:
            grouped = df.groupby(x)[y].agg(agg).reset_index()
            df = grouped
        except Exception:
            pass

    fig = None

    try:
        if chart_type == "bar":
            fig = px.bar(df, x=x, y=y, color=color, title=chart.title,
                         barmode="group", height=height, width=width)
        elif chart_type == "line":
            fig = px.line(df, x=x, y=y, color=color, title=chart.title,
                          height=height, width=width, markers=True)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, color=color, title=chart.title,
                             height=height, width=width, trendline="lowess" if len(df) > 10 else None)
        elif chart_type == "pie":
            fig = px.pie(df, names=x, values=y, title=chart.title,
                         height=height, width=width, hole=0.3)
        elif chart_type == "area":
            fig = px.area(df, x=x, y=y, color=color, title=chart.title,
                          height=height, width=width)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x or y, color=color, title=chart.title,
                               height=height, width=width, nbins=30)
        elif chart_type == "heatmap":
            if x and isinstance(y, str) and y != x:
                pivot = df.pivot_table(index=y, columns=x, aggfunc="size", fill_value=0)
                fig = px.imshow(pivot, title=chart.title, height=height, width=width,
                                color_continuous_scale="Viridis")
            else:
                fig = px.density_heatmap(df, x=x, y=y, title=chart.title,
                                         height=height, width=width)
        elif chart_type == "box":
            fig = px.box(df, x=x, y=y, color=color, title=chart.title,
                         height=height, width=width)
        elif chart_type == "violin":
            fig = px.violin(df, x=x, y=y, color=color, title=chart.title,
                            height=height, width=width, box=True)
        elif chart_type == "sunburst":
            if color:
                fig = px.sunburst(df, path=[x, color], values=y, title=chart.title,
                                  height=height, width=width)
            else:
                fig = px.sunburst(df, path=[x], values=y, title=chart.title,
                                  height=height, width=width)
        elif chart_type == "funnel":
            fig = px.funnel(df, x=x, y=y, title=chart.title, height=height, width=width)
        else:
            # Default: bar chart
            fig = px.bar(df, x=x, y=y, color=color, title=chart.title, height=height, width=width)
    except Exception as exc:
        # Fallback: simple bar chart
        try:
            fig = px.bar(df, title=f"{chart.title} (fallback)", height=height, width=width)
        except Exception:
            fig = go.Figure()
            fig.add_annotation(text=f"Could not render: {exc}", showarrow=False)

    if fig:
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=40, t=50, b=40),
            font=dict(size=12, color="#4a5568"),
            hovermode="x unified" if chart_type in ("line", "area") else "closest",
        )
    return fig or go.Figure()


# ── Auto-dashboard builder ──

def build_dashboard(
    df: pd.DataFrame,
    charts: list[ChartRecommendation],
    title: str = "Dashboard",
    columns: int = 2,
) -> list[go.Figure]:
    """Build a dashboard grid from chart recommendations."""
    figures = []
    for chart in charts:
        fig = render_chart(chart, df)
        figures.append(fig)
    return figures


def auto_dashboard(
    df: pd.DataFrame,
    title: str = "Auto Dashboard",
    max_charts: int = 6,
) -> list[go.Figure]:
    """Auto-generate a dashboard by analyzing the dataframe."""
    charts: list[ChartRecommendation] = []
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(include="object").columns.tolist()
    date_cols = df.select_dtypes(include="datetime").columns.tolist()

    # 1. Time series if date column exists
    if date_cols and numeric_cols:
        for nc in numeric_cols[:2]:
            charts.append(ChartRecommendation(
                chart_type="line",
                title=f"{nc} over Time",
                x_column=date_cols[0],
                y_column=nc,
                aggregation="none",
            ))

    # 2. Categorical distributions
    for cat in categorical_cols[:3]:
        if numeric_cols:
            charts.append(ChartRecommendation(
                chart_type="bar",
                title=f"{cat} by {numeric_cols[0]}",
                x_column=cat,
                y_column=numeric_cols[0],
                aggregation="sum",
            ))
        # Also a pie chart
        charts.append(ChartRecommendation(
            chart_type="pie",
            title=f"{cat} Distribution",
            x_column=cat,
            y_column=numeric_cols[0] if numeric_cols else cat,
            aggregation="count",
        ))

    # 3. Correlation heatmap if enough numeric columns
    if len(numeric_cols) >= 3:
        charts.append(ChartRecommendation(
            chart_type="heatmap",
            title="Correlation Matrix",
            x_column=numeric_cols[0],
            y_column=numeric_cols[1],
            aggregation="none",
        ))

    # 4. Scatter for numeric pairs
    if len(numeric_cols) >= 2:
        charts.append(ChartRecommendation(
            chart_type="scatter",
            title=f"{numeric_cols[0]} vs {numeric_cols[1]}",
            x_column=numeric_cols[0],
            y_column=numeric_cols[1],
            color_column=categorical_cols[0] if categorical_cols else None,
        ))

    # 5. Histograms
    for nc in numeric_cols[:3]:
        charts.append(ChartRecommendation(
            chart_type="histogram",
            title=f"{nc} Distribution",
            x_column=nc,
            y_column=nc,
        ))

    return build_dashboard(df, charts[:max_charts], title=title)


# ── Matplotlib figure to PIL image utility ──

def fig_to_base64(fig: go.Figure) -> str:
    """Convert a Plotly figure to a base64-encoded PNG string."""
    img_bytes = fig.to_image(format="png", width=800, height=500, scale=2)
    return base64.b64encode(img_bytes).decode("utf-8")


def create_kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    icon: str = "📊",
) -> str:
    """Return an HTML KPI card."""
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """
