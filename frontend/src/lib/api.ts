const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  // ── Upload ──
  uploadFile: (file: File, autoClean = true, sep = ',') => {
    const form = new FormData();
    form.append('file', file);
    form.append('auto_clean', String(autoClean));
    form.append('sep', sep);
    return request<{ dataset: import('../types').DatasetInfo; message: string }>('/upload', {
      method: 'POST',
      body: form,
    });
  },

  // ── Database ──
  connectDb: (config: {
    db_type: string; host?: string; port?: number; database?: string;
    user?: string; password?: string; connection_string?: string; connection_name?: string;
  }) =>
    request<{ dataset: import('../types').DatasetInfo; message: string }>('/connect-db', {
      method: 'POST',
      body: JSON.stringify(config),
    }),

  // ── Datasets ──
  listDatasets: () =>
    request<import('../types').DatasetListItem[]>('/datasets'),

  getDataset: (id: string) =>
    request<import('../types').DatasetInfo>(`/datasets/${id}`),

  deleteDataset: (id: string) =>
    request<{ status: string }>(`/datasets/${id}`, { method: 'DELETE' }),

  // ── Query ──
  query: (payload: {
    dataset_id: string; question: string; model?: string; provider?: string;
    system_prompt_key?: string; generate_charts?: boolean;
  }) =>
    request<import('../types').QueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // ── Insights ──
  runInsights: (payload: { dataset_id: string; model?: string; provider?: string }) =>
    request<import('../types').InsightsResponse>('/insights', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // ── Dashboard ──
  generateDashboard: (payload: {
    dataset_id: string; max_charts?: number; use_llm?: boolean; model?: string; provider?: string;
  }) =>
    request<{ charts: Record<string, unknown>[] }>('/generate-dashboard', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // ── Models ──
  listModels: () =>
    request<import('../types').ModelInfo[]>('/models'),

  // ── Settings ──
  getSettings: () =>
    request<import('../types').SettingsInfo>('/settings'),

  updateSettings: (payload: Partial<import('../types').SettingsInfo>) =>
    request<import('../types').SettingsInfo>('/settings', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
};
