"""SQL database data sources: PostgreSQL, MySQL, SQLite, and generic."""

from __future__ import annotations
from typing import Any, Optional

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from data_sources.base import DataSource, Dataset


class SQLDatabaseSource(DataSource):
    """Base class for SQL-based data sources."""

    source_type = "sql"
    display_name = "SQL Database"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.engine = None
        self.connection_string: str = ""

    def connect(self) -> bool:
        if not self.connection_string:
            raise ValueError(f"No connection string for {self.display_name}")
        self.engine = create_engine(
            self.connection_string,
            connect_args={"connect_timeout": 10},
            pool_pre_ping=True,
        )
        # Test connection
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True

    def load(self) -> list[Dataset]:
        if self.engine is None:
            raise RuntimeError("Not connected. Call connect() first.")
        inspector = inspect(self.engine)
        table_names = inspector.get_table_names()
        if not table_names:
            # Try listing views
            try:
                table_names = inspector.get_view_names()
            except Exception:
                pass

        datasets = []
        for table in table_names:
            try:
                df = pd.read_sql_table(table, self.engine)
                datasets.append(Dataset(
                    name=table,
                    df=df,
                    source_type=self.source_type,
                    description=f"Table: {table}",
                ))
            except Exception as exc:
                # If sqlalchemy fails, try raw query
                try:
                    with self.engine.connect() as conn:
                        result = conn.execute(text(f"SELECT * FROM {table} LIMIT 10000"))
                        df = pd.DataFrame(result.fetchall(), columns=result.keys())
                        datasets.append(Dataset(name=table, df=df, source_type=self.source_type))
                except Exception:
                    continue

        return datasets

    def execute_query(self, sql: str) -> pd.DataFrame:
        """Execute a raw SQL query and return a DataFrame."""
        if self.engine is None:
            self.connect()
        return pd.read_sql_query(sql, self.engine)

    def get_schema(self) -> dict[str, list[dict]]:
        """Get schema info for all tables."""
        if self.engine is None:
            self.connect()
        inspector = inspect(self.engine)
        schema = {}
        for table in inspector.get_table_names():
            columns = []
            for col in inspector.get_columns(table):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": col.get("default"),
                })
            schema[table] = columns
        return schema

    def disconnect(self) -> None:
        if self.engine:
            self.engine.dispose()
        self.engine = None


class PostgreSQLSource(SQLDatabaseSource):
    source_type = "postgresql"
    display_name = "PostgreSQL"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.connection_string = self._build_conn_str()

    def _build_conn_str(self) -> str:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 5432)
        db = self.config.get("database") or self.config.get("db") or self.config.get("dbname")
        user = self.config.get("user") or self.config.get("username")
        password = self.config.get("password")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"


class MySQLSource(SQLDatabaseSource):
    source_type = "mysql"
    display_name = "MySQL"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.connection_string = self._build_conn_str()

    def _build_conn_str(self) -> str:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 3306)
        db = self.config.get("database") or self.config.get("db") or self.config.get("dbname")
        user = self.config.get("user") or self.config.get("username")
        password = self.config.get("password")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"


class SQLiteSource(SQLDatabaseSource):
    source_type = "sqlite"
    display_name = "SQLite"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        db_path = self.config.get("database") or self.config.get("db") or self.config.get("file_path")
        self.connection_string = f"sqlite:///{db_path}"


class GenericSQLSource(SQLDatabaseSource):
    """Generic SQLAlchemy-supported database. Provide a full connection string."""

    source_type = "generic_sql"
    display_name = "Generic SQL (via SQLAlchemy)"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.connection_string = self.config.get("connection_string", "")
