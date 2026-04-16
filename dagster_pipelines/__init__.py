from dagster import Definitions

from .assets.dashboard import dashboard
from .assets.eval_run import eval_results
from .assets.score_table import score_table
from .resources.vllm_client import VLLMResource
from .sensors import eval_job, new_checkpoint_sensor

defs = Definitions(
    assets=[eval_results, score_table, dashboard],
    resources={
        "vllm": VLLMResource(
            base_url="http://localhost:8000",
            model_name="Qwen/Qwen2.5-1.5B-Instruct",
        )
    },
    jobs=[eval_job],
    sensors=[new_checkpoint_sensor],
)
