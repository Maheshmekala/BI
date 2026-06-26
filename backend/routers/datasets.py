"""REST endpoints for listing and managing loaded datasets."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.state import state
from backend.schemas import DatasetInfo, ColumnInfo

router = APIRouter()


@router.get("/datasets")
async def list_datasets():
    """List all loaded datasets."""
    return state.list_datasets()


@router.get("/datasets/{ds_id}", response_model=DatasetInfo)
async def get_dataset(ds_id: str):
    """Get full details and preview for a dataset."""
    info = state.dataset_info(ds_id)
    if info is None:
        raise HTTPException(404, "Dataset not found")
    return DatasetInfo(**info)


@router.delete("/datasets/{ds_id}")
async def delete_dataset(ds_id: str):
    """Remove a dataset from memory."""
    if state.remove_dataset(ds_id):
        return {"status": "ok", "message": "Dataset removed"}
    raise HTTPException(404, "Dataset not found")
