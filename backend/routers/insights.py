"""REST endpoint for automated data insights and dashboard generation."""

from __future__ import annotations
import json

from fastapi import APIRouter, HTTPException
import plotly.io as pio

from insights import InsightsEngine
from llm import get_llm
from visualization import render_chart, auto_dashboard
from query_engine import QueryEngine

from backend.state import state
from backend.schemas import InsightRequest, InsightsResponse, DashboardRequest

router = APIRouter()


@router.post("/insights", response_model=InsightsResponse)
async def run_insights(req: InsightRequest):
    """Run full statistical + LLM analysis on a dataset."""
    ds = state.get_dataset(req.dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    try:
        engine = InsightsEngine()
        if req.model and req.provider:
            engine.llm = get_llm(model_name=req.model, provider_name=req.provider)

        analysis = engine.analyze(ds)

        return InsightsResponse(
            overview=analysis.get("overview", {}),
            statistical=analysis.get("statistical", {}),
            correlations=analysis.get("correlations", {}),
            outliers=analysis.get("outliers", {}),
            trends=analysis.get("trends", []),
            kpis=analysis.get("kpis", []),
            llm_insights=analysis.get("llm_insights", ""),
        )

    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.post("/generate-dashboard")
async def generate_dashboard(req: DashboardRequest):
    """Auto-generate a dashboard from a dataset."""
    ds = state.get_dataset(req.dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    try:
        if req.use_llm:
            engine = QueryEngine()
            if req.model and req.provider:
                engine.llm = get_llm(model_name=req.model, provider_name=req.provider)

            result = engine.query(
                question="Design a comprehensive dashboard for this dataset. "
                         "Suggest the most informative visualizations.",
                dataset=ds,
                generate_charts=True,
                system_prompt_key="dashboard_designer",
            )
            charts = result.charts[:req.max_charts]
            figures = [render_chart(chart, ds.df) for chart in charts if render_chart(chart, ds.df)]
        else:
            figures = auto_dashboard(ds.df, title=ds.name, max_charts=req.max_charts)

        chart_data = [json.loads(pio.to_json(fig)) for fig in figures if fig]
        return {"charts": chart_data}

    except Exception as exc:
        raise HTTPException(500, str(exc))
