from datetime import datetime, timezone

from dagster import AssetExecutionContext, AssetIn, asset
from storage.db import ensure_schema, get_connection


@asset(
    ins={"pathvqa_eval_results": AssetIn()},
    group_name="multimodal_evaluation",
)
def multimodal_score_table(
    context: AssetExecutionContext,
    pathvqa_eval_results: dict,
) -> None:
    con = get_connection()
    ensure_schema(con)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    now = datetime.now(timezone.utc)

    con.execute(
        "INSERT INTO multimodal_scores VALUES (?, ?, ?, ?, ?, ?)",
        [
            run_id,
            "pathvqa",
            "yn_accuracy",
            pathvqa_eval_results["accuracy"],
            pathvqa_eval_results["samples_evaluated"],
            now,
        ],
    )
    context.log.info(
        "Stored PathVQA yn_accuracy=%.4f for run %s",
        pathvqa_eval_results["accuracy"],
        run_id,
    )
    con.close()
