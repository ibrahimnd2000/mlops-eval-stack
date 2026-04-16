from lm_eval import simple_evaluate


def run_eval(
    base_url: str,
    model_name: str,
    tasks: list[str],
    num_fewshot: int = 0,
    limit: int | None = None,
) -> dict:
    """Thin wrapper around lm-eval simple_evaluate for a local-completions endpoint."""
    base_url = base_url.rstrip("/")
    return simple_evaluate(
        model="local-completions",
        model_args=f"base_url={base_url}/v1/completions,model={model_name}",
        tasks=tasks,
        num_fewshot=num_fewshot,
        limit=limit,
    )
