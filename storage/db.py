import duckdb
from pathlib import Path

STORAGE_DIR = Path(__file__).resolve().parent
DB_PATH = STORAGE_DIR / "eval_scores.duckdb"


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH))


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            run_id VARCHAR,
            task VARCHAR,
            metric VARCHAR,
            value DOUBLE,
            ran_at TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS latency_reports (
            computed_at TIMESTAMP,
            metric VARCHAR,
            value DOUBLE
        )
    """)
