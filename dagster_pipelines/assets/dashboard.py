from pathlib import Path

import duckdb
from dagster import AssetExecutionContext, AssetIn, MetadataValue, asset

DASHBOARD_PATH = Path("storage/dashboard.html")

_CSS = """
body{font-family:system-ui,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;background:#0f0f1a;color:#e0e0e0}
h1{color:#7c8cf8}h2{color:#4ade80;border-bottom:1px solid #333;padding-bottom:6px;margin-top:32px}
.table{width:100%;border-collapse:collapse;margin-bottom:24px;font-size:14px}
.table th{background:#1e1e2e;color:#7c8cf8;padding:8px 12px;text-align:left}
.table td{padding:8px 12px;border-bottom:1px solid #222}
.table tr:hover td{background:#1a1a2e}
"""


def _table(con: duckdb.DuckDBPyConnection, sql: str) -> str:
    return con.execute(sql).df().to_html(index=False, classes="table", border=0)


@asset(
    ins={"score_table": AssetIn()},
    group_name="evaluation",
)
def dashboard(context: AssetExecutionContext, score_table: None) -> None:
    """Write a static HTML dashboard with benchmark score trends and latency summary."""
    con = duckdb.connect("storage/eval_scores.duckdb")

    scores_html = _table(con, """
        SELECT run_id, task, metric, ROUND(value, 4) AS value, ran_at
        FROM scores
        ORDER BY ran_at DESC
        LIMIT 100
    """)

    latency_html = _table(con, """
        SELECT metric, ROUND(value * 1000, 2) AS value_ms, computed_at
        FROM latency_reports
        ORDER BY computed_at DESC
        LIMIT 20
    """)

    con.close()

    html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>LLM Eval Dashboard</title>
<style>{_CSS}</style></head>
<body>
<h1>LLM Eval Dashboard</h1>
<h2>Benchmark scores</h2>
{scores_html}
<h2>Latency (ms)</h2>
{latency_html}
</body></html>"""

    DASHBOARD_PATH.write_text(html)
    context.add_output_metadata({
        "dashboard_path": MetadataValue.path(str(DASHBOARD_PATH.resolve())),
    })
    context.log.info("Dashboard written to %s", DASHBOARD_PATH)
