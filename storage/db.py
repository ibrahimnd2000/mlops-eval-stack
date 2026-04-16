import duckdb
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "eval_scores.duckdb"


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
