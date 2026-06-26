import { useState } from 'react';
import { api } from '../lib/api';
import { ChartRenderer } from '../components/charts/chart-renderer';
import type { DatasetInfo } from '../types';

interface DashboardPageProps {
  dataset: DatasetInfo;
}

export function DashboardPage({ dataset }: DashboardPageProps) {
  const [maxCharts, setMaxCharts] = useState(6);
  const [useLlm, setUseLlm] = useState(false);
  const [charts, setCharts] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.generateDashboard({
        dataset_id: dataset.id,
        max_charts: maxCharts,
        use_llm: useLlm,
      });
      setCharts(res.charts);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to generate dashboard');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">📊</span>
        <div>
          <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Dashboard Builder</h1>
          <p className="text-sm text-[#718096] m-0">Auto-generate a dashboard or build one manually</p>
        </div>
      </div>

      <div className="flex gap-6 items-end mb-6 p-4 rounded-xl bg-white border border-[#e8ecf0]">
        <div>
          <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">Max charts</label>
          <input
            type="range"
            min={2}
            max={12}
            value={maxCharts}
            onChange={(e) => setMaxCharts(Number(e.target.value))}
            className="w-32"
          />
          <span className="text-sm text-[#4a5568] ml-2">{maxCharts}</span>
        </div>
        <label className="flex items-center gap-2 text-sm text-[#4a5568] cursor-pointer">
          <input type="checkbox" checked={useLlm} onChange={() => setUseLlm(!useLlm)} className="rounded border-[#e2e8f0]" />
          Use LLM for smart layout
        </label>
        <button
          onClick={generate}
          disabled={loading}
          className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-[#1a56db] hover:bg-[#1e60e0] disabled:opacity-40 shadow-sm transition-all active:scale-95"
        >
          {loading ? 'Generating...' : '🚀 Generate Dashboard'}
        </button>
      </div>

      {error && (
        <div className="p-4 mb-4 rounded-xl bg-[#fff5f5] border border-[#e8ecf0] text-sm text-[#e53e3e]">
          {error}
        </div>
      )}

      {charts.length === 0 && !loading && !error && (
        <div className="flex items-center justify-center h-64 text-[#a0aec0] text-sm">
          Click "Generate Dashboard" to create visualizations
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center h-64 text-[#718096] text-sm">
          <div className="flex gap-1.5">
            <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {charts.map((fig, i) => (
          <div key={i} className="p-3 rounded-xl bg-white border border-[#e8ecf0]">
            <ChartRenderer chart={{ figure: fig as Record<string, unknown> }} height={350} />
          </div>
        ))}
      </div>
    </div>
  );
}
