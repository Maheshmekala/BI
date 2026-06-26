"""Abstract base classes for data sources and datasets."""

from __future__ import annotations
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pandas as pd


@dataclass
class Dataset:
    """A single named table / dataframe extracted from a data source."""

    name: str
    df: pd.DataFrame
    description: str = ""
    source_type: str = ""  # csv, excel, postgresql, etc.
    loaded_at: datetime = field(default_factory=datetime.now)
    row_count: int = 0
    column_count: int = 0
    columns_info: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.row_count = len(self.df)
        self.column_count = len(self.df.columns)
        self.columns_info = [
            {
                "name": col,
                "dtype": str(self.df[col].dtype),
                "null_count": int(self.df[col].isna().sum()),
                "unique_count": int(self.df[col].nunique()),
                "sample_values": self.df[col].dropna().unique()[:5].tolist(),
            }
            for col in self.df.columns
        ]

    @property
    def fingerprint(self) -> str:
        """Unique hash of the dataset for caching."""
        raw = json.dumps({
            "name": self.name,
            "cols": list(self.df.columns),
            "shape": self.df.shape,
            "dtypes": {c: str(d) for c, d in self.df.dtypes.items()},
        }, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def summary(self) -> dict:
        """Return a rich summary of the dataset."""
        numeric_cols = self.df.select_dtypes(include="number").columns.tolist()
        categorical_cols = self.df.select_dtypes(include="object").columns.tolist()
        date_cols = self.df.select_dtypes(include="datetime").columns.tolist()
        return {
            "name": self.name,
            "rows": self.row_count,
            "columns": self.column_count,
            "column_names": list(self.df.columns),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "date_columns": date_cols,
            "missing_data": {col: int(self.df[col].isna().sum()) for col in self.df.columns},
            "basic_stats": self.df.describe(include="all").to_dict() if self.row_count > 0 else {},
            "sample": self.df.head(10).to_dict(orient="records"),
        }


class DataSource(ABC):
    """Abstract data source — subclass to support a new file format or database."""

    source_type: str = "abstract"
    display_name: str = "Abstract Source"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._datasets: list[Dataset] = []
        self._connection = None

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection / open the resource. Return True on success."""
        ...

    @abstractmethod
    def load(self) -> list[Dataset]:
        """Load all available datasets. Returns a list of Dataset objects."""
        ...

    def disconnect(self) -> None:
        """Tear down connection."""
        self._connection = None

    @property
    def datasets(self) -> list[Dataset]:
        if not self._datasets:
            self.connect()
            self._datasets = self.load()
        return self._datasets

    @property
    def combined_df(self) -> pd.DataFrame | None:
        """Merge all datasets into one (if there's only one, just return it)."""
        if not self._datasets:
            return None
        if len(self._datasets) == 1:
            return self._datasets[0].df
        # Multiple tables: prefix columns with table name
        merged = pd.concat(
            {ds.name: ds.df for ds in self._datasets},
            axis=1,
        )
        return merged

    def get_dataset(self, name: str) -> Dataset | None:
        for ds in self._datasets:
            if ds.name == name:
                return ds
        return None


class DataSourceRegistry:
    """Registry of available data sources (singleton-style)."""

    _sources: dict[str, DataSource] = {}

    @classmethod
    def register(cls, key: str, source: DataSource) -> None:
        cls._sources[key] = source

    @classmethod
    def get(cls, key: str) -> DataSource | None:
        return cls._sources.get(key)

    @classmethod
    def list(cls) -> dict[str, str]:
        return {k: v.display_name for k, v in cls._sources.items()}

    @classmethod
    def remove(cls, key: str) -> None:
        cls._sources.pop(key, None)

    @classmethod
    def clear(cls) -> None:
        cls._sources.clear()

    @classmethod
    def all_datasets(cls) -> dict[str, list[Dataset]]:
        return {key: src.datasets for key, src in cls._sources.items()}
