import { useState, useEffect, useRef } from 'react';
import { api } from '../lib/api';
import type { DatasetInfo } from '../types';

interface ChartsPageProps {
  dataset: DatasetInfo | null;
}

export function ChartsPage({ dataset }: ChartsPageProps) {
  const [xCol, setXCol] = useState('');
  const [yCol, setYCol] = useState('');
  const [chartType, setChartType] = useState('bar');
  const [figure, setFigure] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const columns = dataset?.columns?.map((c) => c.name) ?? [];

  const renderChart = async () => {
    if (!dataset || !xCol || !yCol) return;
    setLoading(true);
    try {
      const res = await api.query({
        dataset_id: dataset.id,
        question: `Show me ${chartType} chart of ${yCol} by ${xCol}`,
        generate_charts: true,
        system_prompt_key: 'data_analyst',
      });
      if (res.rendered_charts?.length > 0) {
        setFigure(res.rendered_charts[0].figure as unknown as Record<string, unknown>);
      } else {
        const chartRes = await api.query({
          dataset_id: dataset.id,
          question: `Create a ${chartType} chart with x=${xCol}, y=${yCol}`,
          generate_charts: true,
        });
        if (chartRes.rendered_charts?.length > 0) {
          setFigure(chartRes.rendered_charts[0].figure as unknown as Record<string, unknown>);
        }
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (columns.length > 0) {
      setXCol(columns[0]);
      setYCol(columns.length > 1 ? columns[1] : columns[0]);
    }
  }, [dataset?.id]);

  if (!dataset) {
    return (
      <div>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🎨</span>
          <div>
            <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Chart Builder</h1>
            <p className="text-sm text-[#718096] m-0">Build custom visualizations</p>
          </div>
        </div>
        <div className="flex items-center justify-center h-64 text-[#a0aec0] text-sm">Upload data first</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">🎨</span>
        <div>
          <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Chart Builder</h1>
          <p className="text-sm text-[#718096] m-0">Build custom visualizations with your active dataset</p>
        </div>
      </div>

      <div className="grid grid-cols-[300px_1fr] gap-6">
        <div className="space-y-4 p-5 rounded-xl bg-white border border-[#e8ecf0]">
          <div>
            <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">Chart Type</label>
            <select value={chartType} onChange={(e) => setChartType(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]">
              {['bar', 'line', 'scatter', 'pie', 'area', 'histogram', 'box', 'violin', 'heatmap', 'funnel'].map((t) => (
                <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">X Column</label>
            <select value={xCol} onChange={(e) => setXCol(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]">
              {columns.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">Y Column</label>
            <select value={yCol} onChange={(e) => setYCol(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]">
              {columns.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <button onClick={renderChart} disabled={loading}
            className="w-full px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-[#1a56db] hover:bg-[#1e60e0] disabled:opacity-40 transition-all">
            {loading ? 'Rendering...' : 'Render Chart'}
          </button>
        </div>

        <div className="p-4 rounded-xl bg-white border border-[#e8ecf0] min-h-[400px] flex items-center justify-center">
          {figure ? (
            <PlotlyFigure figure={figure} />
          ) : (
            <p className="text-sm text-[#a0aec0]">Select columns and click Render Chart</p>
          )}
        </div>
      </div>
    </div>
  );
}

function PlotlyFigure({ figure }: { figure: Record<string, unknown> }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    import('plotly.js-dist-min').then((Plotly) => {
      if (!ref.current) return;
      const layout = { ...((figure.layout as Record<string, unknown>) || {}), paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' };
      Plotly.default.newPlot(ref.current, figure.data as unknown[], layout, { responsive: true, displayModeBar: false });
    });
    return () => {
      if (ref.current) {
        import('plotly.js-dist-min').then((Plotly) => Plotly.default.purge(ref.current));
      }
    };
  }, [figure]);

  return <div ref={ref} className="w-full h-[400px]" />;
}
