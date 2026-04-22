import mlflow
from dagster import AssetExecutionContext, AssetIn, asset


@asset(
    ins={
        "eval_results": AssetIn(),
        "pathvqa_eval_results": AssetIn(),
    },
    group_name="registry",
)
def model_registry_entry(
    context: AssetExecutionContext,
    eval_results: dict,
    pathvqa_eval_results: dict,
) -> None:
    mlflow.set_tracking_uri("file:./storage/mlruns")
    mlflow.set_experiment("kaiko-eval-stack")

    with mlflow.start_run(run_name=context.run_id):
        for task, metrics in eval_results.items():
            for metric, value in metrics.items():
                if isinstance(value, float):
                    clean_metric = metric.replace(",", "_")
                    mlflow.log_metric(f"{task}/{clean_metric}", value)

        mlflow.log_metric("pathvqa/yn_accuracy", pathvqa_eval_results["accuracy"])

        mlflow.log_params({
            "text_model": "Qwen2.5-1.5B-Instruct",
            "vision_model": "llava-1.5-7b-hf",
            "pathvqa_samples": pathvqa_eval_results["samples_evaluated"],
        })

    context.log.info("Logged run to MLflow: %s", context.run_id)
