"""Instant BI — FastAPI Backend

Provides a REST API that wraps the existing Python data sources, LLM providers,
query engine, insights engine, and visualization modules.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure the project root is on sys.path so we can import existing modules
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import datasets, query, insights, models, settings, sources

app = FastAPI(
    title="Instant BI API",
    version="2.0.0",
    description="REST API for Instant BI — chat with your data",
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(sources.router, prefix="/api", tags=["Sources"])
app.include_router(datasets.router, prefix="/api", tags=["Datasets"])
app.include_router(query.router, prefix="/api", tags=["Query"])
app.include_router(insights.router, prefix="/api", tags=["Insights"])
app.include_router(models.router, prefix="/api", tags=["Models"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Instant BI"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
