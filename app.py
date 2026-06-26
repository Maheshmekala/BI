#!/usr/bin/env python3
"""
Instant BI — Chat with your data.
Upload CSV/Excel/PDF, connect to databases, ask questions in natural language,
and get instant dashboards, reports, KPIs, and insights powered by LLMs.
"""

from __future__ import annotations

import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import streamlit as st

# Ensure the app root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

# ── Page must be the first Streamlit command ──
st.set_page_config(
    page_title="Instant BI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load custom CSS — right after set_page_config, before page rendering ──
css_path = Path(__file__).parent / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Helper: Ray background HTML (Bolt-style) ──

RAY_BG_HTML = """
<div class="bolt-ray-bg">
    <div class="bolt-ray-radial"></div>
    <div class="bolt-ray-rings">
        <div class="bolt-ring bolt-ring-5" style="z-index:5;border:12px solid white;margin-top:-10px"></div>
        <div class="bolt-ring bolt-ring-4" style="z-index:4;border:18px solid #dbeafe;margin-top:-8px"></div>
        <div class="bolt-ring bolt-ring-3" style="z-index:3;border:18px solid #bfdbfe;margin-top:-6px"></div>
        <div class="bolt-ring bolt-ring-2" style="z-index:2;border:18px solid #93bbfc;margin-top:-3px"></div>
        <div class="bolt-ring bolt-ring-1" style="z-index:1;border:16px solid #3b82f6;box-shadow:0 -10px 20px rgba(59,130,246,0.3)"></div>
    </div>
</div>
<style>
.bolt-ray-bg {
    position: fixed; inset:0; width:100%; height:100%;
    pointer-events:none; overflow:hidden; z-index:0;
}
.bolt-ray-radial {
    position:absolute; left:50%; transform:translateX(-50%);
    width:4000px; height:1800px;
    background:radial-gradient(circle at center 800px, rgba(59,130,246,0.15) 0%, rgba(59,130,246,0.06) 14%, rgba(59,130,246,0.03) 18%, transparent 22%, transparent 25%);
}
.bolt-ray-rings {
    position:absolute; top:175px; left:50%;
    width:1600px; height:1600px;
    transform:translate(-50%) rotate(180deg);
}
.bolt-ring {
    position:absolute; inset:0; border-radius:50%;
    background:#ffffff;
}
@media (min-width:640px) {
    .bolt-ray-radial { width:6000px; }
    .bolt-ray-rings { top:50%; width:3043px; height:2865px; }
}
</style>
"""

# ── Imports ──
from config.settings import settings
from data_sources import (
    DataSource, DataSourceRegistry, Dataset,
    CSVSource, ExcelSource, PDFSource,
    PostgreSQLSource, MySQLSource, SQLiteSource, GenericSQLSource,
    ALL_SOURCES,
)
from llm import get_llm, get_available_models, PROVIDER_MAP, SYSTEM_PROMPTS, LLMMessage
from query_engine import QueryEngine
from visualization import render_chart, build_dashboard, auto_dashboard
from visualization.renderers import (
    display_query_result, display_auto_dashboard, display_kpi_row,
    display_data_preview, display_chart_selector,
)
from insights import InsightsEngine
from utils import auto_clean_df, profile_dataset, sanitize_filename


# ========================================================================
# SESSION STATE INIT
# ========================================================================

def init_session_state() -> None:
    """Initialize all session state variables."""
    defaults = {
        "registered_sources": {},
        "active_dataset": None,
        "active_source_key": None,
        "chat_history": [],
        "query_engine": QueryEngine(),
        "insights_engine": InsightsEngine(),
        "current_model": None,
        "current_provider": None,
        "available_models": [],
        "data_profiles": {},
        "selected_tables": {},
        "db_connections": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Initialize llm if needed
    if st.session_state.current_model is None or st.session_state.current_provider is None:
        avail = get_available_models()
        st.session_state.available_models = avail
        if avail:
            st.session_state.current_model = avail[0]["id"]
            st.session_state.current_provider = avail[0]["provider"]
            st.session_state.query_engine.llm = get_llm(
                model_name=avail[0]["id"],
                provider_name=avail[0]["provider"],
            )
            st.session_state.insights_engine.llm = get_llm(
                model_name=avail[0]["id"],
                provider_name=avail[0]["provider"],
            )


init_session_state()


# ========================================================================
# SIDEBAR — NAVIGATION + MODEL SELECTION + DATA SOURCE MANAGEMENT
# ========================================================================

def render_sidebar() -> str:
    """Render the sidebar and return the selected page."""
    with st.sidebar:
        st.markdown(
            f'<div class="bolt-sidebar-header">'
            f'<span class="bolt-sidebar-icon">⚡</span>'
            f'<span class="bolt-sidebar-title">Instant BI</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="text-align: center; color: #a0aec0; font-size: 0.8rem; margin-top: -8px;">'
            f'Chat with your data</p>',
            unsafe_allow_html=True,
        )
        st.divider()

        # ── Navigation ──
        nav_items = [
            ("Chat & Analyze", "💬", "chat"),
            ("Dashboard Builder", "📊", "dashboard"),
            ("Auto Insights", "💡", "insights"),
            ("Data Sources", "🗄️", "sources"),
            ("Chart Builder", "🎨", "charts"),
            ("Settings", "⚙️", "settings"),
        ]
        page_map = {
            "chat": "Chat & Analyze",
            "dashboard": "Dashboard Builder",
            "insights": "Auto Insights",
            "sources": "Data Sources",
            "charts": "Chart Builder",
            "settings": "Settings",
        }
        page = page_map.get(st.session_state.get("_active_page", "chat"), "Chat & Analyze")

        for label, icon, key in nav_items:
            _is_active = st.session_state.get("_active_page", "chat") == key or page == label
            btn_type = "primary" if _is_active else "secondary"
            if st.button(f"{icon} {label}", key=f"nav_{key}", use_container_width=True, type=btn_type):
                st.session_state["_active_page"] = key
                page = label

        st.divider()

        # ── Model Selector ──
        st.markdown("### ⚡ Model")
        models = st.session_state.available_models
        if not models:
            st.warning("No LLM providers configured. Add API keys to .env")
        else:
            model_options = {m["name"]: m for m in models}
            # Show the current model as a nice badge
            current_name = next((m["name"] for m in models if m["id"] == st.session_state.current_model), models[0]["name"])
            st.markdown(
                f'<div class="bolt-model-badge">'
                f'<span class="bolt-dot"></span>'
                f'<span>{current_name}</span></div>',
                unsafe_allow_html=True
            )
            # Find the index of the current model in the list
            try:
                current_model_name = next(m["name"] for m in models if m["id"] == st.session_state.current_model)
                default_idx = list(model_options.keys()).index(current_model_name)
            except (StopIteration, ValueError):
                default_idx = 0
            selected_name = st.selectbox(
                "Select model",
                options=list(model_options.keys()),
                index=default_idx,
                key="model_select",
                label_visibility="collapsed",
            )
            selected = model_options[selected_name]
            if (st.session_state.current_model != selected["id"]
                    or st.session_state.current_provider != selected["provider"]):
                st.session_state.current_model = selected["id"]
                st.session_state.current_provider = selected["provider"]
                st.session_state.query_engine.llm = get_llm(
                    model_name=selected["id"],
                    provider_name=selected["provider"],
                )
                st.session_state.insights_engine.llm = get_llm(
                    model_name=selected["id"],
                    provider_name=selected["provider"],
                )
                st.rerun()

        st.divider()

        # ── Quick Stats ──
        if st.session_state.active_dataset is not None:
            ds = st.session_state.active_dataset
            st.markdown(
                f'<div style="background:rgba(20,136,252,0.06);border:1px solid rgba(20,136,252,0.15);'
                f'border-radius:10px;padding:12px;margin-bottom:8px;">'
                f'<div style="font-size:0.75rem;color:#8a8a8f;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:6px;">📋 Active Data</div>'
                f'<div style="font-size:0.9rem;color:#e0e0e0;font-weight:500;">{ds.name}</div>'
                f'<div style="font-size:0.8rem;color:#8a8a8f;margin-top:2px;">{ds.row_count:,} rows · {ds.column_count} cols</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button("🔄 Clear & New", key="clear_data", use_container_width=True, type="secondary"):
                st.session_state.active_dataset = None
                st.session_state.active_source_key = None
                st.session_state.chat_history = []
                st.rerun()

        # ── Source count ──
        src_count = len(DataSourceRegistry._sources)
        st.caption(f"Total data sources: {src_count}")

    return page


# ========================================================================
# PAGE 1: CHAT & ANALYZE
# ========================================================================

def page_chat_analyze() -> None:
    active_ds = st.session_state.active_dataset

    if active_ds is None:
        # ── Bolt-style landing page (compact) ──
        st.markdown(RAY_BG_HTML, unsafe_allow_html=True)

        st.markdown('<div class="bolt-landing-compact">', unsafe_allow_html=True)

        # Announcement badge
        st.markdown(
            f'<div style="text-align:center;margin-top:8px;">'
            f'<a class="bolt-announcement" href="#" target="_blank">'
            f'<span class="bolt-announcement-glow"></span>'
            f'<span class="bolt-announcement-shine"></span>'
            f'⚡ Introducing Instant BI V2</a></div>',
            unsafe_allow_html=True
        )

        # Title
        st.markdown(
            f'<div class="bolt-hero-compact-title">'
            f'What will you <span class="bolt-hero-gradient">analyze</span> today?'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="text-align:center;color:#718096;font-size:0.95rem;font-weight:500;'
            f'margin:8px auto 0;max-width:500px;line-height:1.4;">Upload data, connect databases, and get instant '
            f'dashboards, reports & insights powered by AI.</div>',
            unsafe_allow_html=True
        )

        # Quick action buttons
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("📁 Upload Data", key="landing_upload", use_container_width=True, type="primary"):
                    st.session_state["_active_page"] = "sources"
                    st.rerun()
            with b2:
                if st.button("🔌 Connect DB", key="landing_db", use_container_width=True, type="secondary"):
                    st.session_state["_active_page"] = "sources"
                    st.rerun()
            with b3:
                if st.button("📖 Quick Start", key="landing_help", use_container_width=True, type="secondary"):
                    pass

        # Quick-start tips right below buttons
        st.markdown(
            '<div style="display:flex;gap:16px;justify-content:center;margin-top:32px;flex-wrap:wrap;">'
            '<div style="display:flex;align-items:center;gap:8px;background:#f7fafc;border:1px solid #e8ecf0;border-radius:10px;padding:10px 18px;">'
            '<span style="font-size:1.3rem;">📁</span>'
            '<span style="font-size:0.8rem;color:#4a5568;">Upload CSV / Excel / PDF</span></div>'
            '<div style="display:flex;align-items:center;gap:8px;background:#f7fafc;border:1px solid #e8ecf0;border-radius:10px;padding:10px 18px;">'
            '<span style="font-size:1.3rem;">💬</span>'
            '<span style="font-size:0.8rem;color:#4a5568;">Ask questions in plain English</span></div>'
            '<div style="display:flex;align-items:center;gap:8px;background:#f7fafc;border:1px solid #e8ecf0;border-radius:10px;padding:10px 18px;">'
            '<span style="font-size:1.3rem;">📊</span>'
            '<span style="font-size:0.8rem;color:#4a5568;">Auto-generated dashboards</span></div>'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Show dataset context
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        '<span style="font-size:1.8rem;">💬</span>'
        '<span style="font-size:1.5rem;font-weight:700;'
        'background:linear-gradient(135deg,#60a5fa,#3b82f6);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">'
        'Chat & Analyze</span>'
        f'<span style="font-size:0.75rem;color:#5a5a5f;margin-left:auto;'
        f'background:rgba(20,136,252,0.1);border:1px solid rgba(20,136,252,0.2);'
        f'border-radius:999px;padding:4px 12px;">⚡ {active_ds.name}</span>'
        '</div>',
        unsafe_allow_html=True
    )
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Dataset", active_ds.name)
        col2.metric("Rows", f"{active_ds.row_count:,}")
        col3.metric("Columns", active_ds.column_count)
        col4.metric("Numeric", len(active_ds.df.select_dtypes(include="number").columns))

        with st.expander("👁️ Preview Data"):
            display_data_preview(active_ds.df)

    # ── Chat container ──
    chat_container = st.container()

    # Display chat history
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                # Show charts if present
                if msg.get("charts"):
                    for i, chart_rec in enumerate(msg["charts"]):
                        try:
                            fig = render_chart(chart_rec, active_ds.df)
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception:
                            pass

    # ── Chat input ──
    if prompt := st.chat_input("Ask a question about your data..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                # Determine if this is a dashboard request
                is_dashboard = any(kw in prompt.lower() for kw in
                                    ["dashboard", "kpi", "overview", "summarize everything"])

                result = st.session_state.query_engine.query(
                    question=prompt,
                    dataset=active_ds,
                    generate_charts=True,
                    system_prompt_key="dashboard_designer" if is_dashboard else "data_analyst",
                )

                if result.error:
                    st.error(result.error)
                    msg = result.error
                else:
                    st.markdown(result.answer)
                    msg = result.answer

                # Render charts
                charts_shown = []
                if result.charts:
                    st.subheader("📈 Visualizations")
                    cols = st.columns(2)
                    for i, chart_rec in enumerate(result.charts):
                        with cols[i % 2]:
                            try:
                                fig = render_chart(chart_rec, active_ds.df)
                                st.plotly_chart(fig, use_container_width=True)
                                charts_shown.append(chart_rec)
                            except Exception as exc:
                                st.caption(f"Could not render chart: {exc}")

                # Also show model info
                st.caption(
                    f"Response from {result.metadata.get('provider', 'unknown')} · "
                    f"Model: {result.metadata.get('model', 'unknown')} · "
                    f"{result.metadata.get('latency_ms', 0):.0f}ms"
                )

        # Save to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": msg,
            "charts": charts_shown if charts_shown else None,
        })


# ========================================================================
# PAGE 2: DASHBOARD BUILDER
# ========================================================================

def page_dashboard_builder() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:14px;margin-bottom:0;">'
        '<span style="font-size:2.2rem;">📊</span>'
        '<div><p style="font-size:1.8rem;font-weight:800;margin:0;color:#1a202c;">Dashboard Builder</p>'
        '<p style="margin:0;font-size:0.85rem;color:#718096;">Auto-generate a dashboard or build one manually</p></div>'
        '</div>',
        unsafe_allow_html=True
    )

    active_ds = st.session_state.active_dataset

    if active_ds is None:
        st.info("👈 No active dataset. Go to **Data Sources** first.")
        return

    df = active_ds.df

    tab1, tab2 = st.tabs(["🤖 Auto Dashboard", "🎨 Manual Build"])

    with tab1:
        st.markdown("Let AI automatically build a dashboard based on your data.")

        col1, col2 = st.columns([1, 3])
        with col1:
            max_charts = st.slider("Max charts", 2, 12, 6)
            use_llm = st.checkbox("Use LLM for smart layout", value=False)

        with col2:
            if st.button("🚀 Generate Auto Dashboard", use_container_width=True, type="primary"):
                figures = []
                if use_llm:
                    # Get LLM recommendations
                    with st.spinner("Asking AI to design a dashboard..."):
                        result = st.session_state.query_engine.query(
                            question="Design a comprehensive dashboard for this dataset. "
                                     "Suggest the most informative visualizations.",
                            dataset=active_ds,
                            generate_charts=True,
                            system_prompt_key="dashboard_designer",
                        )
                        if result.charts:
                            figures = build_dashboard(df, result.charts[:max_charts])

                # Fallback: rule-based auto dashboard (used when LLM returns no charts, or LLM is off)
                if not figures:
                    figures = auto_dashboard(df, title=active_ds.name, max_charts=max_charts)

                if figures:
                    cols = st.columns(2)
                    for i, fig in enumerate(figures):
                        with cols[i % 2]:
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Not enough columns to generate charts. Try uploading a dataset with more numeric columns.")

        # Quick auto-dashboard button
        if st.button("📈 Quick Dashboard (rule-based)", use_container_width=True):
            figures = auto_dashboard(df, title=active_ds.name, max_charts=8)
            if figures:
                cols = st.columns(2)
                for i, fig in enumerate(figures):
                    with cols[i % 2]:
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Not enough columns to generate charts.")

    with tab2:
        display_chart_selector(df)


# ========================================================================
# PAGE 3: AUTO INSIGHTS
# ========================================================================

def page_auto_insights() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:14px;margin-bottom:0;">'
        '<span style="font-size:2.2rem;">💡</span>'
        '<div><p style="font-size:1.8rem;font-weight:800;margin:0;color:#1a202c;">Auto Insights & KPIs</p>'
        '<p style="margin:0;font-size:0.85rem;color:#718096;">Automatically discover patterns, outliers, and actionable insights</p></div>'
        '</div>',
        unsafe_allow_html=True
    )

    active_ds = st.session_state.active_dataset

    if active_ds is None:
        st.info("👈 No active dataset. Go to **Data Sources** first.")
        return

    df = active_ds.df

    if st.button("🔍 Run Full Analysis", type="primary", use_container_width=True):
        with st.spinner("Running deep analysis... This may take a moment."):
            engine = st.session_state.insights_engine
            analysis = engine.analyze(active_ds)

            # ── KPI Cards ──
            st.subheader("🎯 Key Performance Indicators")
            kpis = analysis.get("kpis", [])
            if kpis:
                cols = st.columns(min(len(kpis), 5))
                for i, kpi in enumerate(kpis):
                    with cols[i % 5]:
                        delta_color = "normal" if kpi.get("direction") == "neutral" else (
                            "normal" if kpi.get("is_good") else "inverse"
                        )
                        st.metric(
                            label=f"{kpi.get('icon', '')} {kpi.get('label', '')}",
                            value=kpi.get("value", ""),
                            delta=kpi.get("delta"),
                            delta_color=delta_color,
                        )

            # ── Overview ──
            with st.expander("📋 Dataset Overview", expanded=True):
                overview = analysis.get("overview", {})
                cols = st.columns(4)
                cols[0].metric("Rows", overview.get("rows", 0))
                cols[1].metric("Columns", overview.get("columns", 0))
                cols[2].metric("Completeness", f"{overview.get('completeness', 0)}%")
                cols[3].metric("Duplicates", overview.get("duplicate_rows", 0))

            # ── Statistical Summary ──
            stats = analysis.get("statistical", {})
            if stats and "message" not in stats:
                with st.expander("📐 Statistical Summary", expanded=False):
                    stats_df = pd.DataFrame(stats).T
                    st.dataframe(stats_df, use_container_width=True)

            # ── Correlations ──
            corr_data = analysis.get("correlations", {})
            if corr_data.get("significant_pairs"):
                with st.expander("🔗 Significant Correlations", expanded=True):
                    for pair in corr_data["significant_pairs"][:10]:
                        direction = "📈" if pair["direction"] == "positive" else "📉"
                        st.markdown(
                            f"{direction} **{pair['col1']}** ↔ **{pair['col2']}**: "
                            f"*{pair['correlation']}* ({pair['strength']}, {pair['direction']})"
                        )

            # ── Outliers ──
            outliers = analysis.get("outliers", {})
            if outliers:
                with st.expander("⚠️ Detected Outliers", expanded=True):
                    for col, info in outliers.items():
                        st.markdown(
                            f"**{col}**: {info['count']} outliers ({info['percentage']}%) — "
                            f"outside [{info['lower_bound']:.2f}, {info['upper_bound']:.2f}]"
                        )

            # ── Trends ──
            trends = analysis.get("trends", [])
            if trends:
                with st.expander("📈 Trends", expanded=True):
                    for trend in trends[:10]:
                        icon = "🟢" if trend.get("trend") == "upward" else "🔴"
                        sig = "✅" if trend.get("significant") else ""
                        st.markdown(
                            f"{icon} **{trend['column']}**: {trend['trend']} trend "
                            f"(slope={trend['slope']}, R²={trend['r_squared']}) {sig}"
                        )

            # ── LLM Insights ──
            llm_text = analysis.get("llm_insights", "")
            if llm_text and "Could not generate" not in llm_text:
                with st.expander("🧠 AI-Generated Insights", expanded=True):
                    st.markdown(llm_text)
            else:
                with st.expander("🧠 AI-Generated Insights", expanded=False):
                    st.info("LLM insights unavailable. Check your API key.")

    else:
        st.info("Click **Run Full Analysis** to discover insights in your data.")

        # Show what we'll analyze
        with st.expander("What will be analyzed?"):
            st.markdown("""
            - **KPIs** — automatically identified key metrics with trends
            - **Statistical Summary** — mean, median, std, skewness, kurtosis per column
            - **Correlations** — significant relationships between numeric columns
            - **Outliers** — IQR-based outlier detection
            - **Trends** — linear regression trends over row index
            - **AI Insights** — LLM-generated narrative insights and recommendations
            """)


# ========================================================================
# PAGE 4: DATA SOURCES
# ========================================================================

def page_data_sources() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:14px;margin-bottom:0;">'
        '<span style="font-size:2.2rem;">🗄️</span>'
        '<div><p style="font-size:1.8rem;font-weight:800;margin:0;color:#1a202c;">Data Sources</p>'
        '<p style="margin:0;font-size:0.85rem;color:#718096;">Upload files or connect to databases</p></div>'
        '</div>',
        unsafe_allow_html=True
    )

    tab_upload, tab_db, tab_manage = st.tabs(["📁 Upload File", "🔌 Database", "📋 Manage Sources"])

    # ── Tab: Upload File ──
    with tab_upload:
        col1, col2 = st.columns([1, 1])
        with col1:
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=["csv", "xlsx", "xls", "pdf"],
                help="Supported: CSV, Excel (.xlsx/.xls), PDF",
            )
        with col2:
            st.markdown("##### File Options")
            clean_data = st.checkbox("Auto-clean data", value=True)
            if uploaded_file and uploaded_file.name.endswith(".csv"):
                sep = st.text_input("Delimiter", value=",")
            else:
                sep = ","

        if uploaded_file:
            # Save uploaded file
            upload_dir = settings.UPLOAD_DIR
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / sanitize_filename(uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            source_key = sanitize_filename(uploaded_file.name)

            # Load based on extension
            ext = Path(uploaded_file.name).suffix.lower()
            if ext == ".csv":
                source = CSVSource({"file_path": str(file_path), "sep": sep})
            elif ext in (".xlsx", ".xls"):
                source = ExcelSource({"file_path": str(file_path)})
            elif ext == ".pdf":
                source = PDFSource({"file_path": str(file_path)})
            else:
                st.error(f"Unsupported file type: {ext}")
                return

            try:
                datasets = source.datasets
                DataSourceRegistry.register(source_key, source)

                if len(datasets) == 1:
                    ds = datasets[0]
                    if clean_data:
                        ds.df = auto_clean_df(ds.df)
                    st.session_state.active_dataset = ds
                    st.session_state.active_source_key = source_key
                    st.success(f"✅ Loaded **{ds.name}** ({ds.row_count} rows × {ds.column_count} cols)")

                    display_data_preview(ds.df)

                    # Auto profile
                    prof = profile_dataset(ds.df)
                    st.caption(f"Memory: {prof['memory_mb']:.2f} MB | "
                               f"Duplicates: {prof['duplicate_rows']} | "
                               f"Missing cells: {sum(prof['missing'].values())}")
                else:
                    # Multiple sheets/tables
                    st.success(f"Loaded {len(datasets)} tables/sheets:")
                    for ds in datasets:
                        if clean_data:
                            ds.df = auto_clean_df(ds.df)
                        st.markdown(f"- **{ds.name}**: {ds.row_count} rows × {ds.column_count} cols")
                        if st.button(f"Select {ds.name}", key=f"sel_{ds.name}"):
                            st.session_state.active_dataset = ds
                            st.session_state.active_source_key = source_key
                            st.rerun()

            except Exception as exc:
                st.error(f"❌ Error loading file: {exc}")

    # ── Tab: Database ──
    with tab_db:
        st.markdown("Connect to a SQL database to query it in real time.")

        db_type = st.selectbox("Database Type",
                               ["PostgreSQL", "MySQL", "SQLite", "Other (SQLAlchemy URL)"])

        # Connection form (no submit button inside — we use a standalone button instead for progress)
        if db_type == "PostgreSQL":
            host = st.text_input("Host", "localhost", key="pg_host")
            port = st.number_input("Port", value=5432, key="pg_port")
            db_name = st.text_input("Database", key="pg_db")
            user = st.text_input("Username", "postgres", key="pg_user")
            password = st.text_input("Password", type="password", key="pg_pass")
            conn_name = st.text_input("Connection Name", value="My Postgres", key="pg_conn")
            connect_clicked = st.button("🔌 Connect", use_container_width=True, type="primary", key="db_connect_btn")

            if connect_clicked:
                config = {
                    "host": host, "port": int(port),
                    "database": db_name, "user": user, "password": password,
                }
                status = st.status("🔌 Connecting to PostgreSQL...", expanded=True)
                try:
                    status.write("⏳ Resolving host...")
                    status.write("🔐 Authenticating...")
                    source = PostgreSQLSource(config)
                    status.write("📋 Fetching tables...")
                    datasets = source.datasets
                    DataSourceRegistry.register(conn_name, source)
                    st.session_state.active_dataset = datasets[0] if datasets else None
                    status.update(label="✅ Connected", state="complete", expanded=False)
                    st.success(f"Found {len(datasets)} tables in '{conn_name}'")
                except Exception as exc:
                    status.update(label=f"❌ Connection failed", state="error")
                    st.error(f"Connection failed: {exc}")

        elif db_type == "MySQL":
            host = st.text_input("Host", "localhost", key="my_host")
            port = st.number_input("Port", value=3306, key="my_port")
            db_name = st.text_input("Database", key="my_db")
            user = st.text_input("Username", "root", key="my_user")
            password = st.text_input("Password", type="password", key="my_pass")
            conn_name = st.text_input("Connection Name", "My MySQL", key="my_conn")
            connect_clicked = st.button("🔌 Connect", use_container_width=True, type="primary", key="db_connect_btn")

            if connect_clicked:
                config = {
                    "host": host, "port": int(port),
                    "database": db_name, "user": user, "password": password,
                }
                status = st.status("🔌 Connecting to MySQL...", expanded=True)
                try:
                    status.write("⏳ Resolving host...")
                    status.write("🔐 Authenticating...")
                    source = MySQLSource(config)
                    status.write("📋 Fetching tables...")
                    datasets = source.datasets
                    DataSourceRegistry.register(conn_name, source)
                    st.session_state.active_dataset = datasets[0] if datasets else None
                    status.update(label="✅ Connected", state="complete", expanded=False)
                    st.success(f"Found {len(datasets)} tables in '{conn_name}'")
                except Exception as exc:
                    status.update(label=f"❌ Connection failed", state="error")
                    st.error(f"Connection failed: {exc}")

        elif db_type == "SQLite":
            db_path = st.text_input("SQLite File Path", key="lite_path")
            conn_name = st.text_input("Connection Name", "My SQLite", key="lite_conn")
            connect_clicked = st.button("🔌 Connect", use_container_width=True, type="primary", key="db_connect_btn")

            if connect_clicked:
                status = st.status("🔌 Opening SQLite database...", expanded=True)
                try:
                    status.write("📂 Opening file...")
                    source = SQLiteSource({"database": db_path})
                    status.write("📋 Reading tables...")
                    datasets = source.datasets
                    DataSourceRegistry.register(conn_name, source)
                    st.session_state.active_dataset = datasets[0] if datasets else None
                    status.update(label="✅ Connected", state="complete", expanded=False)
                    st.success(f"Found {len(datasets)} tables in '{conn_name}'")
                except Exception as exc:
                    status.update(label=f"❌ Connection failed", state="error")
                    st.error(f"Connection failed: {exc}")

        else:  # Other
            conn_url = st.text_input("SQLAlchemy Connection URL",
                                     placeholder="postgresql://user:pass@host:5432/db",
                                     key="gen_url")
            conn_name = st.text_input("Connection Name", "My DB", key="gen_conn")
            connect_clicked = st.button("🔌 Connect", use_container_width=True, type="primary", key="db_connect_btn")

            if connect_clicked:
                status = st.status("🔌 Connecting via SQLAlchemy...", expanded=True)
                try:
                    status.write("⏳ Resolving connection...")
                    source = GenericSQLSource({"connection_string": conn_url})
                    status.write("📋 Fetching tables...")
                    datasets = source.datasets
                    DataSourceRegistry.register(conn_name, source)
                    st.session_state.active_dataset = datasets[0] if datasets else None
                    status.update(label="✅ Connected", state="complete", expanded=False)
                    st.success(f"Found {len(datasets)} tables in '{conn_name}'")
                except Exception as exc:
                    status.update(label=f"❌ Connection failed", state="error")
                    st.error(f"Connection failed: {exc}")

    # ── Tab: Manage Sources ──
    with tab_manage:
        st.markdown("### Registered Data Sources")
        registry = DataSourceRegistry._sources

        if not registry:
            st.info("No data sources registered yet.")
        else:
            for key, source in list(registry.items()):
                with st.container(border=True):
                    st.markdown(f"**{source.display_name}**: `{key}`")
                    try:
                        datasets = source.datasets
                        for ds in datasets:
                            if st.button(f"📊 Load **{ds.name}**", key=f"load_{key}_{ds.name}"):
                                st.session_state.active_dataset = ds
                                st.session_state.active_source_key = key
                                st.session_state.chat_history = []
                                st.success(f"Activated: {ds.name}")
                                st.rerun()
                            st.caption(f"  {ds.row_count} rows × {ds.column_count} cols · "
                                       f"Loaded: {ds.loaded_at.strftime('%H:%M:%S')}")
                    except Exception as exc:
                        st.error(f"Error loading: {exc}")

                    if st.button(f"🗑️ Remove", key=f"del_{key}"):
                        DataSourceRegistry.remove(key)
                        if st.session_state.active_source_key == key:
                            st.session_state.active_dataset = None
                            st.session_state.active_source_key = None
                        st.rerun()


# ========================================================================
# PAGE 5: CHART BUILDER
# ========================================================================

def page_chart_builder() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:14px;margin-bottom:0;">'
        '<span style="font-size:2.2rem;">🎨</span>'
        '<div><p style="font-size:1.8rem;font-weight:800;margin:0;color:#1a202c;">Chart Builder</p>'
        '<p style="margin:0;font-size:0.85rem;color:#718096;">Build custom visualizations with your active dataset</p></div>'
        '</div>',
        unsafe_allow_html=True
    )

    active_ds = st.session_state.active_dataset
    if active_ds is None:
        st.info("👈 No active dataset. Upload data from **Data Sources** first.")
        return

    display_chart_selector(active_ds.df)


# ========================================================================
# PAGE 6: SETTINGS
# ========================================================================

def page_settings() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:14px;margin-bottom:0;">'
        '<span style="font-size:2.2rem;">⚙️</span>'
        '<div><p style="font-size:1.8rem;font-weight:800;margin:0;color:#1a202c;">Settings</p>'
        '<p style="margin:0;font-size:0.85rem;color:#718096;">Configure application behavior</p></div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── LLM Configuration ──
    with st.expander("🤖 LLM Configuration", expanded=True):
        st.markdown("Configure your LLM providers via the `.env` file or environment variables.")

        # Show current status
        st.markdown("#### Provider Status")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Groq", "✅ Configured" if settings.GROQ_API_KEY else "❌ Not set")
        col2.metric("OpenAI", "✅ Configured" if settings.OPENAI_API_KEY else "❌ Not set")
        col3.metric("Anthropic", "✅ Configured" if settings.ANTHROPIC_API_KEY else "❌ Not set")
        col4.metric("Google", "✅ Configured" if settings.GOOGLE_API_KEY else "❌ Not set")
        col5.metric("Ollama (Local)", "🟢 Always available")

        st.markdown("#### System Prompts")
        prompt_key = st.selectbox("View / Edit Prompt", list(SYSTEM_PROMPTS.keys()))
        st.text_area("System Prompt", value=SYSTEM_PROMPTS[prompt_key], height=200,
                     key=f"prompt_{prompt_key}")

    # ── Data Configuration ──
    with st.expander("📁 Data Configuration", expanded=False):
        max_mb = st.number_input("Max Upload Size (MB)", value=settings.MAX_UPLOAD_SIZE_MB,
                                 min_value=10, max_value=2000)
        col1, col2 = st.columns(2)
        col1.metric("Upload Directory", str(settings.UPLOAD_DIR))
        col2.metric("Cache TTL", f"{settings.CACHE_TTL_SECONDS}s")

    # ── Session Info ──
    with st.expander("ℹ️ Session Info", expanded=False):
        st.json({
            "model": st.session_state.current_model,
            "provider": st.session_state.current_provider,
            "active_source": st.session_state.active_source_key,
            "chat_messages": len(st.session_state.chat_history),
            "registered_sources": len(DataSourceRegistry._sources),
        })

    # ── Danger Zone ──
    with st.expander("⚠️ Danger Zone", expanded=False):
        if st.button("🗑️ Clear All Session Data", type="secondary", use_container_width=True):
            safe_keys = [k for k in st.session_state.keys() if not k.startswith("_")]
            for key in safe_keys:
                del st.session_state[key]
            st.rerun()

        if st.button("🗑️ Clear All Registered Sources", type="secondary", use_container_width=True):
            DataSourceRegistry.clear()
            st.session_state.active_dataset = None
            st.session_state.active_source_key = None
            st.rerun()


# ========================================================================
# MAIN
# ========================================================================

def main() -> None:
    page = render_sidebar()

    # Render the selected page — wrap everything for dark background
    page_map = {
        "Chat & Analyze": page_chat_analyze,
        "Dashboard Builder": page_dashboard_builder,
        "Auto Insights": page_auto_insights,
        "Data Sources": page_data_sources,
        "Chart Builder": page_chart_builder,
        "Settings": page_settings,
    }

    # Only show ray BG on chat page when no data is loaded
    if page != "Chat & Analyze" or st.session_state.active_dataset is not None:
        # Dark page wrapper for non-landing pages
        st.markdown('<div class="bolt-page">', unsafe_allow_html=True)

    page_map[page]()

    if page != "Chat & Analyze" or st.session_state.active_dataset is not None:
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
