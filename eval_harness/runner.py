import time

from lm_eval import simple_evaluate
from openai import OpenAI

from inference.observer import TokenObserver

_PROBE_PROMPT = "The capital of France is"
_PROBE_MAX_TOKENS = 32


def _probe_latency(base_url: str, model_name: str, n: int = 5) -> None:
    client = OpenAI(base_url=f"{base_url}/v1", api_key="dummy")
    observer = TokenObserver()
    for _ in range(n):
        t0 = time.perf_counter()
        first_token_t = None
        completion_tokens = 0
        stream = client.completions.create(
            model=model_name,
            prompt=_PROBE_PROMPT,
            max_tokens=_PROBE_MAX_TOKENS,
            stream=True,
        )
        for chunk in stream:
            if first_token_t is None:
                first_token_t = time.perf_counter()
            if chunk.choices[0].text:
                completion_tokens += 1
        t1 = time.perf_counter()
        observer.record(
            prompt_tokens=len(_PROBE_PROMPT.split()),
            completion_tokens=max(completion_tokens, 1),
            ttft_s=(first_token_t or t1) - t0,
            total_s=t1 - t0,
            model=model_name,
        )


def run_eval(
    base_url: str,
    model_name: str,
    tasks: list[str],
    num_fewshot: int = 0,
    limit: int | None = None,
) -> dict:
    """Thin wrapper around lm-eval simple_evaluate for a local-completions endpoint."""
    base_url = base_url.rstrip("/")
    _probe_latency(base_url, model_name)
    return simple_evaluate(
        model="local-completions",
        model_args=f"base_url={base_url}/v1/completions,model={model_name}",
        tasks=tasks,
        num_fewshot=num_fewshot,
        limit=limit,
    )
