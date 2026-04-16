import json
from datetime import datetime, timezone

from dagster import AssetExecutionContext, AssetIn, asset
from storage.db import STORAGE_DIR, ensure_schema, get_connection

LOG_PATH = STORAGE_DIR / "token_metrics.jsonl"


def _percentile(sorted_data: list[float], p: int) -> float:
    idx = int(len(sorted_data) * p / 100)
    return sorted_data[min(idx, len(sorted_data) - 1)]


@asset(
    ins={"eval_results": AssetIn()},
    group_name="evaluation",
)
def score_table(context: AssetExecutionContext, eval_results: dict) -> None:
    """Normalise and store eval scores + token metrics; export Parquet snapshots."""
    con = get_connection()
    ensure_schema(con)

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

    # parquet snapshots — use absolute paths so COPY works regardless of CWD
    scores_parquet = str(STORAGE_DIR / "scores.parquet")
    latency_parquet = str(STORAGE_DIR / "latency_reports.parquet")
    con.execute(f"COPY scores TO '{scores_parquet}' (FORMAT PARQUET)")
    con.execute(f"COPY latency_reports TO '{latency_parquet}' (FORMAT PARQUET)")
    con.close()
