"""Renderers for Streamlit — bridges visualization engine with the UI."""

from __future__ import annotations
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from query_engine.engine import ChartRecommendation, QueryResult
from visualization import render_chart, build_dashboard, auto_dashboard
from visualization import create_kpi_card


def display_query_result(
    result: QueryResult,
    df: pd.DataFrame | None = None,
) -> None:
    """Display a QueryResult in Streamlit."""
    if result.error:
        st.error(f"⚠️ {result.error}")
        return

    # Show answer
    if result.answer:
        with st.container(border=True):
            st.markdown(result.answer)

    # Show SQL if present
    if result.sql_query:
        with st.expander("📝 SQL Query", expanded=False):
            st.code(result.sql_query, language="sql")

    # Show charts
    if result.charts:
        st.subheader("📈 Visualizations")
        cols = st.columns(2)
        for i, chart_rec in enumerate(result.charts):
            with cols[i % 2]:
                if df is not None:
                    fig = render_chart(chart_rec, df)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"Chart suggestion: **{chart_rec.title}** ({chart_rec.chart_type})")


def display_auto_dashboard(
    df: pd.DataFrame,
    title: str = "Auto Dashboard",
    max_charts: int = 8,
) -> None:
    """Auto-generate and display a dashboard."""
    with st.spinner("Generating dashboard..."):
        try:
            figures = auto_dashboard(df, title=title, max_charts=max_charts)
            cols = st.columns(2)
            for i, fig in enumerate(figures):
                with cols[i % 2]:
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            st.warning(f"Could not auto-generate dashboard: {exc}")


def display_kpi_row(kpis: list[dict], columns: int = 4) -> None:
    """Display a row of KPI cards."""
    cols = st.columns(columns)
    for i, kpi in enumerate(kpis):
        with cols[i % columns]:
            html = create_kpi_card(
                label=kpi.get("label", ""),
                value=kpi.get("value", ""),
                delta=kpi.get("delta"),
                icon=kpi.get("icon", "📊"),
            )
            st.markdown(html, unsafe_allow_html=True)


def display_data_preview(df: pd.DataFrame, max_rows: int = 100) -> None:
    """Show a data preview with column stats."""
    st.dataframe(
        df.head(max_rows),
        use_container_width=True,
        height=min(400, 35 * min(len(df), max_rows)),
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{len(df):,}")
    col2.metric("Columns", len(df.columns))
    col3.metric("Numeric", len(df.select_dtypes(include="number").columns))
    col4.metric("Missing cells", int(df.isna().sum().sum()))


def display_chart_selector(df: pd.DataFrame) -> None:
    """Interactive chart builder UI."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    all_cols = df.columns.tolist()

    with st.form("chart_builder"):
        st.markdown("### 🎨 Custom Chart Builder")

        col1, col2 = st.columns(2)
        with col1:
            chart_type = st.selectbox(
                "Chart Type",
                ["bar", "line", "scatter", "pie", "area", "histogram",
                 "box", "violin", "heatmap", "sunburst", "funnel"],
            )
            x_col = st.selectbox("X-axis", all_cols)

        with col2:
            y_col = st.selectbox("Y-axis (or values)", all_cols if chart_type != "histogram" else ["_count"])
            color_col = st.selectbox("Color (optional)", ["None"] + all_cols)
            agg_method = st.selectbox("Aggregation", ["None", "sum", "mean", "count", "min", "max"])

        title = st.text_input("Chart Title", value=f"{chart_type.title()} Chart")

        submitted = st.form_submit_button("🎨 Generate Chart", use_container_width=True)

    if submitted:
        rec = ChartRecommendation(
            chart_type=chart_type,
            title=title,
            x_column=x_col,
            y_column=y_col if y_col != "_count" else x_col,
            aggregation=agg_method.lower() if agg_method != "None" else "none",
            color_column=color_col if color_col != "None" else None,
        )
        try:
            fig = render_chart(rec, df)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            st.error(f"Could not render chart: {exc}")
