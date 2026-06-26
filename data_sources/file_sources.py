"""File-based data sources: CSV, Excel, PDF."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import pdfplumber

from data_sources.base import DataSource, Dataset


class CSVSource(DataSource):
    source_type = "csv"
    display_name = "CSV File"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.file_path: Optional[Path] = None

    def connect(self) -> bool:
        path = self.config.get("file_path") or self.config.get("path")
        if not path:
            raise ValueError("CSVSource requires 'file_path' in config")
        self.file_path = Path(path)
        return self.file_path.exists()

    def load(self) -> list[Dataset]:
        kwargs = {
            "sep": self.config.get("sep", ","),
            "encoding": self.config.get("encoding", "utf-8"),
            "low_memory": self.config.get("low_memory", False),
        }
        # auto-detect encoding
        encodings = ["utf-8", "latin1", "cp1252", "iso-8859-1"]
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(self.file_path, **{**kwargs, "encoding": enc})
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if df is None:
            df = pd.read_csv(self.file_path, **{**kwargs, "encoding": "utf-8", "encoding_errors": "replace"})

        name = self.file_path.stem.replace(" ", "_").replace("-", "_")
        return [Dataset(name=name, df=df, source_type="csv")]


class ExcelSource(DataSource):
    source_type = "excel"
    display_name = "Excel File"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.file_path: Optional[Path] = None

    def connect(self) -> bool:
        path = self.config.get("file_path") or self.config.get("path")
        if not path:
            raise ValueError("ExcelSource requires 'file_path' in config")
        self.file_path = Path(path)
        return self.file_path.exists()

    def load(self) -> list[Dataset]:
        excel_file = pd.ExcelFile(self.file_path, engine="openpyxl")
        sheet_names = excel_file.sheet_names
        datasets = []
        for sheet in sheet_names:
            df = pd.read_excel(self.file_path, sheet_name=sheet, engine="openpyxl")
            name = f"{self.file_path.stem}_{sheet}".replace(" ", "_").replace("-", "_")
            datasets.append(Dataset(name=name, df=df, source_type="excel"))
        return datasets


class PDFSource(DataSource):
    source_type = "pdf"
    display_name = "PDF File"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.file_path: Optional[Path] = None

    def connect(self) -> bool:
        path = self.config.get("file_path") or self.config.get("path")
        if not path:
            raise ValueError("PDFSource requires 'file_path' in config")
        self.file_path = Path(path)
        return self.file_path.exists()

    def _extract_tables(self) -> list[pd.DataFrame]:
        """Extract tabular data from PDF pages."""
        tables = []
        with pdfplumber.open(self.file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                extracted = page.extract_table()
                if extracted and len(extracted) > 1:
                    headers = extracted[0]
                    rows = extracted[1:]
                    df = pd.DataFrame(rows, columns=headers)
                    # clean
                    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
                    df = df.replace("", pd.NA).dropna(how="all")
                    if len(df) > 0:
                        tables.append((f"table_page_{page_num + 1}", df))
        return tables

    def _extract_text(self) -> pd.DataFrame | None:
        """Fallback: extract raw text into a single-column dataframe."""
        lines = []
        with pdfplumber.open(self.file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines.extend(text.split("\n"))
        if not lines:
            return None
        df = pd.DataFrame({"content": [l for l in lines if l.strip()]})
        return df

    def load(self) -> list[Dataset]:
        datasets = []

        # First try tables
        tables = self._extract_tables()
        for name, df in tables:
            ds_name = f"{self.file_path.stem}_{name}".replace(" ", "_").replace("-", "_")
            datasets.append(Dataset(name=ds_name, df=df, source_type="pdf", description=f"Extracted table from {name}"))

        # Fallback text extraction
        if not datasets:
            text_df = self._extract_text()
            if text_df is not None and len(text_df) > 0:
                name = self.file_path.stem.replace(" ", "_").replace("-", "_")
                datasets.append(Dataset(name=name, df=text_df, source_type="pdf", description="Extracted text content"))

        return datasets
