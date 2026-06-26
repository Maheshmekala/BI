"""REST endpoints for LLM-powered query and chat."""

from __future__ import annotations
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from llm import get_llm, get_available_models, SYSTEM_PROMPTS, LLMMessage
from query_engine import QueryEngine
from query_engine.engine import ChartRecommendation
from visualization import render_chart
from data_sources.base import Dataset
import plotly.io as pio

from backend.state import state
from backend.schemas import QueryRequest, QueryResponse, ChartRenderRequest, ChartRenderResponse

router = APIRouter()


def _chart_to_json(chart: ChartRecommendation, df, model_id: str | None = None, provider: str | None = None) -> dict[str, Any] | None:
    """Render a chart recommendation to a Plotly JSON dict."""
    try:
        fig = render_chart(chart, df)
        fig_json = json.loads(pio.to_json(fig))
        return {
            "chart_type": chart.chart_type,
            "title": chart.title,
            "x_column": chart.x_column,
            "y_column": chart.y_column,
            "figure": fig_json,
            "description": chart.description,
        }
    except Exception as exc:
        return None


def _get_dataset(ds_id: str) -> Dataset:
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")
    return ds


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Ask a natural language question about a dataset."""
    ds = _get_dataset(req.dataset_id)

    try:
        # Build query engine with optional model override
        engine = QueryEngine()
        if req.model and req.provider:
            engine.llm = get_llm(model_name=req.model, provider_name=req.provider)

        result = engine.query(
            question=req.question,
            dataset=ds,
            generate_charts=req.generate_charts,
            system_prompt_key=req.system_prompt_key,
        )

        if result.error:
            return QueryResponse(
                answer=result.answer,
                error=result.error,
                metadata=result.metadata,
            )

        # Render charts to Plotly JSON
        rendered = []
        for chart in result.charts:
            fig_data = _chart_to_json(chart, ds.df)
            if fig_data:
                rendered.append(fig_data)

        return QueryResponse(
            answer=result.answer,
            charts=[ChartRecommendation(**c.__dict__) for c in result.charts],
            rendered_charts=rendered,
            metadata=result.metadata,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.post("/query/stream")
async def query_stream(req: QueryRequest):
    """Stream a natural language query response via SSE."""
    ds = _get_dataset(req.dataset_id)

    engine = QueryEngine()
    if req.model and req.provider:
        engine.llm = get_llm(model_name=req.model, provider_name=req.provider)

    async def event_stream():
        try:
            system = SYSTEM_PROMPTS.get(req.system_prompt_key, SYSTEM_PROMPTS["data_analyst"])
            context = engine._build_dataset_context(ds)

            user_parts = [context, f"User question: {req.question}"]
            if req.generate_charts:
                user_parts.append(
                    "\n\nAfter your analysis, if appropriate, provide chart recommendations "
                    "in a JSON code block."
                )

            user_prompt = "\n\n".join(user_parts)
            messages = [
                LLMMessage(role="system", content=system),
                LLMMessage(role="user", content=user_prompt),
            ]

            # Use streaming from the LLM provider
            if engine.llm.supports_streaming:
                full_text = ""
                for chunk in engine.llm.chat_stream(messages):
                    if chunk:
                        full_text += chunk
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

                # After streaming, parse charts
                if req.generate_charts:
                    # Re-run to get charts (streaming doesn't return structured data)
                    non_stream_result = engine.query(
                        question=req.question,
                        dataset=ds,
                        generate_charts=True,
                        system_prompt_key=req.system_prompt_key,
                    )
                    rendered = []
                    for chart in non_stream_result.charts:
                        fig_data = _chart_to_json(chart, ds.df)
                        if fig_data:
                            rendered.append(fig_data)

                    if rendered:
                        yield f"data: {json.dumps({'type': 'charts', 'content': rendered})}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            else:
                # Non-streaming fallback
                result = engine.query(
                    question=req.question,
                    dataset=ds,
                    generate_charts=req.generate_charts,
                    system_prompt_key=req.system_prompt_key,
                )
                yield f"data: {json.dumps({'type': 'text', 'content': result.answer})}\n\n"

                rendered = []
                for chart in result.charts:
                    fig_data = _chart_to_json(chart, ds.df)
                    if fig_data:
                        rendered.append(fig_data)
                if rendered:
                    yield f"data: {json.dumps({'type': 'charts', 'content': rendered})}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/render-chart", response_model=ChartRenderResponse)
async def render_chart_endpoint(req: ChartRenderRequest):
    """Render a single chart recommendation from a dataset."""
    ds = _get_dataset(req.dataset_id)
    try:
        engine = QueryEngine()
        result = engine.query(
            question=req.question,
            dataset=ds,
            generate_charts=True,
            system_prompt_key=req.system_prompt_key,
        )
        if result.charts:
            fig_data = _chart_to_json(result.charts[0], ds.df)
            if fig_data:
                return ChartRenderResponse(figure_json=fig_data.get("figure"))
        return ChartRenderResponse(error="No charts generated")
    except Exception as exc:
        return ChartRenderResponse(error=str(exc))
