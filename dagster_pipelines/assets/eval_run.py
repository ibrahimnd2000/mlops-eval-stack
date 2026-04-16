from dagster import AssetExecutionContext, MetadataValue, asset
from eval_harness.runner import run_eval

from ..resources.vllm_client import VLLMResource


@asset(group_name="evaluation")
def eval_results(context: AssetExecutionContext, vllm: VLLMResource) -> dict:
    """Run lm-eval-harness and return the scores dict (task → metric → value)."""
    output = run_eval(
        base_url=vllm.base_url,
        model_name=vllm.model_name,
        tasks=["hellaswag", "arc_easy"],
        num_fewshot=0,
        limit=50,
    )

    scores = output["results"]

    context.add_output_metadata({
        "hellaswag_acc": MetadataValue.float(scores["hellaswag"]["acc,none"]),
        "arc_easy_acc": MetadataValue.float(scores["arc_easy"]["acc,none"]),
        "num_tasks": MetadataValue.int(len(scores)),
    })
    return scores
