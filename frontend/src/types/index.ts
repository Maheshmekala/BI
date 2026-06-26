export interface DatasetInfo {
  id: string;
  name: string;
  source_type: string;
  description: string;
  row_count: number;
  column_count: number;
  columns: ColumnInfo[];
  preview_rows: Record<string, unknown>[];
  summary_stats: Record<string, unknown>;
}

export interface DatasetListItem {
  id: string;
  name: string;
  source_type: string;
  row_count: number;
  column_count: number;
}

export interface ColumnInfo {
  name: string;
  dtype: string;
  null_count: number;
  unique_count: number;
  sample_values: unknown[];
}

export interface ChartRecommendation {
  chart_type: string;
  title: string;
  x_column: string;
  y_column: string | string[];
  aggregation: string;
  color_column?: string;
  description?: string;
}

export interface RenderedChart {
  chart_type: string;
  title: string;
  x_column: string;
  y_column: string | string[];
  figure: PlotlyFigure;
  description?: string;
}

export interface PlotlyFigure {
  data: Record<string, unknown>[];
  layout: Record<string, unknown>;
}

export interface QueryResponse {
  answer: string;
  charts: ChartRecommendation[];
  rendered_charts: RenderedChart[];
  error?: string;
  metadata: Record<string, unknown>;
}

export interface InsightsResponse {
  overview: Record<string, unknown>;
  statistical: Record<string, unknown>;
  correlations: Record<string, unknown>;
  outliers: Record<string, unknown>;
  trends: TrendInfo[];
  kpis: KpiInfo[];
  llm_insights: string;
  error?: string;
}

export interface TrendInfo {
  column: string;
  trend: string;
  slope: number;
  r_squared: number;
  significant: boolean;
}

export interface KpiInfo {
  label: string;
  value: string;
  delta?: string;
  icon?: string;
  direction?: string;
  is_good?: boolean;
}

export interface ModelInfo {
  id: string;
  provider: string;
  name: string;
}

export interface SettingsInfo {
  app_name: string;
  debug: boolean;
  groq_api_key: string;
  openai_api_key: string;
  anthropic_api_key: string;
  google_api_key: string;
  groq_default_model: string;
  openai_default_model: string;
  anthropic_default_model: string;
  google_default_model: string;
  ollama_default_model: string;
  max_upload_size_mb: number;
  cache_ttl_seconds: number;
  available_providers: string[];
}

export interface SSEEvent {
  type: 'text' | 'charts' | 'error' | 'done';
  content: unknown;
}
