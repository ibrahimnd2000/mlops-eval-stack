import os
import tempfile

from dagster import AssetExecutionContext, MetadataValue, asset
from datasets import load_dataset

from ..resources.vllm_multimodal_client import VLLMMultimodalResource


@asset(group_name="multimodal_evaluation")
def pathvqa_eval_results(
    context: AssetExecutionContext,
    vllm_multimodal: VLLMMultimodalResource,
) -> dict:
    # streaming=True fetches one example at a time — avoids loading 32k pathology
    # images into RAM at once, which OOM-killed the container previously.
    stream = load_dataset("flaviagiammarino/path-vqa", split="test", streaming=True)

    target = 50
    correct = 0
    results = []
    seen = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        for item in stream:
            if item["answer"] not in ("yes", "no"):
                continue
            if seen >= target:
                break

            img_path = os.path.join(tmpdir, f"img_{seen}.jpg")
            item["image"].save(img_path)

            response = vllm_multimodal.complete_with_image(
                prompt=f'{item["question"]} Answer yes or no.',
                image_path=img_path,
            )
            pred = response["text"].strip().lower()
            is_correct = item["answer"] in pred
            correct += is_correct
            results.append({
                "question": item["question"],
                "answer": item["answer"],
                "prediction": pred,
                "correct": is_correct,
                "ttft_s": response["ttft_s"],
            })
            seen += 1

            if seen % 10 == 0:
                context.log.info("Progress: %d/%d", seen, target)

    accuracy = correct / seen
    context.add_output_metadata({
        "pathvqa_yn_accuracy": MetadataValue.float(accuracy),
        "samples_evaluated": MetadataValue.int(seen),
        "correct": MetadataValue.int(correct),
    })
    return {
        "accuracy": accuracy,
        "results": results,
        "samples_evaluated": seen,
    }
