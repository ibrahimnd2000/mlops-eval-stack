from dagster import Definitions, EnvVar

from .assets.dashboard import dashboard
from .assets.eval_run import eval_results
from .assets.mlflow_registry import model_registry_entry
from .assets.mllm_eval_run import pathvqa_eval_results
from .assets.multimodal_score_table import multimodal_score_table
from .assets.score_table import score_table
from .resources.vllm_client import VLLMResource
from .resources.vllm_multimodal_client import VLLMMultimodalResource
from .sensors import eval_job, multimodal_eval_job, new_checkpoint_sensor, registry_job

defs = Definitions(
    assets=[
        eval_results,
        score_table,
        dashboard,
        pathvqa_eval_results,
        multimodal_score_table,
        model_registry_entry,
    ],
    resources={
        "vllm": VLLMResource(
            base_url=EnvVar("VLLM_BASE_URL"),
            model_name=EnvVar("VLLM_MODEL_NAME"),
        ),
        "vllm_multimodal": VLLMMultimodalResource(
            base_url=EnvVar("VLLM_MULTIMODAL_BASE_URL"),
            model_name=EnvVar("VLLM_MULTIMODAL_MODEL_NAME"),
        ),
    },
    jobs=[eval_job, multimodal_eval_job, registry_job],
    sensors=[new_checkpoint_sensor],
)
