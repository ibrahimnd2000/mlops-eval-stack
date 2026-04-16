import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from dagster import AssetExecutionContext, AssetIn, asset

LOG_PATH = Path("storage/token_metrics.jsonl")


def _percentile(sorted_data: list[float], p: int) -> float:
    idx = int(len(sorted_data) * p / 100)
    return sorted_data[min(idx, len(sorted_data) - 1)]


@asset(
    ins={"eval_results": AssetIn()},
    group_name="evaluation",
)
def score_table(context: AssetExecutionContext, eval_results: dict) -> None:
    """Normalise and store eval scores + token metrics; export Parquet snapshots."""
    con = duckdb.connect("storage/eval_scores.duckdb")
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

    # eval scores
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    now = datetime.now(timezone.utc)
    score_rows = [
        (run_id, task, metric, value, now)
        for task, metrics in eval_results["results"].items()
        for metric, value in metrics.items()
        if isinstance(value, float)
    ]
    con.executemany("INSERT INTO scores VALUES (?, ?, ?, ?, ?)", score_rows)
    context.log.info("Stored %d score rows for run %s", len(score_rows), run_id)

    # token metrics from observer log
    if LOG_PATH.exists():
        records = [json.loads(line) for line in LOG_PATH.read_text().splitlines() if line]
        if records:
            ttft = sorted(r["ttft_s"] for r in records)
            tps = sorted(r["throughput_tps"] for r in records)
            con.executemany(
                "INSERT INTO latency_reports VALUES (?, ?, ?)",
                [
                    (now, "ttft_p50", _percentile(ttft, 50)),
                    (now, "ttft_p95", _percentile(ttft, 95)),
                    (now, "ttft_p99", _percentile(ttft, 99)),
                    (now, "tps_p50", _percentile(tps, 50)),
                    (now, "tps_p95", _percentile(tps, 95)),
                    (now, "tps_p99", _percentile(tps, 99)),
                ],
            )
            context.log.info("Stored latency percentiles from %d token records", len(records))

    # parquet snapshots
    con.execute("COPY scores TO 'storage/scores.parquet' (FORMAT PARQUET)")
    con.execute("COPY latency_reports TO 'storage/latency_reports.parquet' (FORMAT PARQUET)")
    con.close()
