"""Pydantic schemas for the Instant BI API."""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Dataset ──

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    null_count: int = 0
    unique_count: int = 0
    sample_values: list[Any] = []


class DatasetInfo(BaseModel):
    id: str
    name: str
    source_type: str = ""
    description: str = ""
    row_count: int = 0
    column_count: int = 0
    columns: list[ColumnInfo] = []
    preview_rows: list[dict[str, Any]] = []
    summary_stats: dict[str, Any] = {}


class DatasetListItem(BaseModel):
    id: str
    name: str
    source_type: str
    row_count: int
    column_count: int


# ── Upload / DB Connect ──

class UploadResponse(BaseModel):
    dataset: DatasetInfo
    message: str = ""


class DBConnectRequest(BaseModel):
    db_type: str = Field(..., pattern="^(PostgreSQL|MySQL|SQLite|Other)$")
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    user: str = "postgres"
    password: str = ""
    connection_string: str = ""
    connection_name: str = "My DB"


class DBConnectResponse(BaseModel):
    dataset: DatasetInfo
    message: str = ""


# ── Query ──

class QueryRequest(BaseModel):
    dataset_id: str
    question: str
    model: str | None = None
    provider: str | None = None
    system_prompt_key: str = "data_analyst"
    generate_charts: bool = True


class ChartRecommendation(BaseModel):
    chart_type: str = "bar"
    title: str = ""
    x_column: str = ""
    y_column: str | list[str] = ""
    aggregation: str = "none"
    color_column: str | None = None
    description: str = ""


class QueryResponse(BaseModel):
    answer: str = ""
    charts: list[ChartRecommendation] = []
    rendered_charts: list[dict[str, Any]] = []
    error: str | None = None
    metadata: dict[str, Any] = {}


# ── Dashboard ──

class DashboardRequest(BaseModel):
    dataset_id: str
    max_charts: int = 6
    use_llm: bool = False
    model: str | None = None
    provider: str | None = None


class InsightRequest(BaseModel):
    dataset_id: str
    model: str | None = None
    provider: str | None = None


class DashboardResponse(BaseModel):
    charts: list[dict[str, Any]]
    error: str | None = None


# ── Insights ──

class InsightsResponse(BaseModel):
    overview: dict[str, Any] = {}
    statistical: dict[str, Any] = {}
    correlations: dict[str, Any] = {}
    outliers: dict[str, Any] = {}
    trends: list[dict[str, Any]] = []
    kpis: list[dict[str, Any]] = []
    llm_insights: str = ""
    error: str | None = None


# ── Models ──

class ModelInfo(BaseModel):
    id: str
    provider: str
    name: str


# ── Settings ──

class SettingsResponse(BaseModel):
    app_name: str = "Instant BI"
    debug: bool = False
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    groq_default_model: str = ""
    openai_default_model: str = ""
    anthropic_default_model: str = ""
    google_default_model: str = ""
    ollama_default_model: str = ""
    max_upload_size_mb: int = 200
    cache_ttl_seconds: int = 3600
    available_providers: list[str] = []


class SettingsUpdateRequest(BaseModel):
    groq_default_model: str | None = None
    openai_default_model: str | None = None
    anthropic_default_model: str | None = None
    google_default_model: str | None = None
    max_upload_size_mb: int | None = None
    cache_ttl_seconds: int | None = None


# ── Chart Render ──

class ChartRenderRequest(BaseModel):
    chart_type: str = "bar"
    title: str = ""
    x_column: str = ""
    y_column: str | list[str] = ""
    aggregation: str = "none"
    color_column: str | None = None


class ChartRenderResponse(BaseModel):
    figure_json: dict[str, Any] | None = None
    error: str | None = None
