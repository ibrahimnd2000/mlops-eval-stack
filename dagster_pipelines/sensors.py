import os

from dagster import RunRequest, SensorEvaluationContext, define_asset_job, sensor

eval_job = define_asset_job("eval_job", selection=["eval_results", "score_table", "dashboard"])


@sensor(job=eval_job, minimum_interval_seconds=30)
def new_checkpoint_sensor(context: SensorEvaluationContext):
    checkpoint_dir = "checkpoints/"
    if not os.path.isdir(checkpoint_dir):
        return

    known = set(context.cursor.split(",")) if context.cursor else set()
    current = {f for f in os.listdir(checkpoint_dir) if f.endswith(".bin")}
    new_checkpoints = current - known

    for ckpt in new_checkpoints:
        yield RunRequest(
            run_key=ckpt,
            run_config={"resources": {"vllm": {"config": {"model_name": ckpt}}}},
        )

    context.update_cursor(",".join(current))
