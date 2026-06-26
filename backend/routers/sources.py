"""REST endpoints for file upload and database connection."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import pandas as pd

from config.settings import settings as app_settings
from data_sources import (
    CSVSource, ExcelSource, PDFSource,
    PostgreSQLSource, MySQLSource, SQLiteSource,
    DataSourceRegistry,
)
from data_sources.sql_sources import GenericSQLSource
from utils import sanitize_filename, auto_clean_df, profile_dataset

from backend.state import state
from backend.schemas import (
    UploadResponse, DBConnectRequest, DBConnectResponse,
    DatasetInfo, ColumnInfo,
)

router = APIRouter()


def _build_dataset_info(ds_id: str, dataset) -> DatasetInfo:
    """Build a DatasetInfo schema from a Dataset object."""
    summary = dataset.summary()
    columns = []
    for c in dataset.df.columns:
        info = {
            "name": c,
            "dtype": str(dataset.df[c].dtype),
            "null_count": int(dataset.df[c].isna().sum()),
            "unique_count": int(dataset.df[c].nunique()),
            "sample_values": dataset.df[c].dropna().unique()[:5].tolist(),
        }
        columns.append(ColumnInfo(**info))
    return DatasetInfo(
        id=ds_id,
        name=dataset.name,
        source_type=dataset.source_type,
        description=dataset.description,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        columns=columns,
        preview_rows=summary.get("sample", []),
        summary_stats=summary.get("basic_stats", {}),
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    auto_clean: bool = Form(True),
    sep: str = Form(","),
):
    """Upload a CSV, Excel, or PDF file and load it as a dataset."""
    upload_dir = app_settings.UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(file.filename or "uploaded_file")
    file_path = upload_dir / safe_name

    # Save uploaded file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    ext = Path(file.filename or "").suffix.lower()
    try:
        if ext == ".csv":
            source = CSVSource({"file_path": str(file_path), "sep": sep})
        elif ext in (".xlsx", ".xls"):
            source = ExcelSource({"file_path": str(file_path)})
        elif ext == ".pdf":
            source = PDFSource({"file_path": str(file_path)})
        else:
            raise HTTPException(400, f"Unsupported file type: {ext}")

        datasets = source.datasets
        if not datasets:
            raise HTTPException(400, "No datasets could be extracted from the file")

        ds = datasets[0]
        if auto_clean:
            ds.df = auto_clean_df(ds.df)

        ds_id = state.add_dataset(ds, source)
        state.current_dataset_id = ds_id
        info = _build_dataset_info(ds_id, ds)

        prof = profile_dataset(ds.df)
        prof_msg = (
            f"Memory: {prof['memory_mb']:.2f} MB | "
            f"Duplicates: {prof['duplicate_rows']} | "
            f"Missing cells: {sum(prof['missing'].values())}"
        )

        return UploadResponse(
            dataset=info,
            message=f"Loaded {ds.name} ({ds.row_count} rows × {ds.column_count} cols). {prof_msg}",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Error loading file: {exc}")


@router.post("/connect-db", response_model=DBConnectResponse)
async def connect_database(req: DBConnectRequest):
    """Connect to a database and load tables as a dataset."""
    try:
        if req.db_type == "PostgreSQL":
            config = {
                "host": req.host,
                "port": req.port or 5432,
                "database": req.database,
                "user": req.user,
                "password": req.password,
            }
            source = PostgreSQLSource(config)
        elif req.db_type == "MySQL":
            config = {
                "host": req.host,
                "port": req.port or 3306,
                "database": req.database,
                "user": req.user,
                "password": req.password,
            }
            source = MySQLSource(config)
        elif req.db_type == "SQLite":
            source = SQLiteSource({"database": req.database})
        else:
            source = GenericSQLSource({"connection_string": req.connection_string})

        datasets = source.datasets
        if not datasets:
            raise HTTPException(400, "No tables found in the database")

        ds = datasets[0]
        ds_id = state.add_dataset(ds, source)
        state.current_dataset_id = ds_id
        info = _build_dataset_info(ds_id, ds)

        return DBConnectResponse(
            dataset=info,
            message=f"Connected! Found {len(datasets)} table(s). Loaded '{ds.name}'.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Database connection failed: {exc}")
