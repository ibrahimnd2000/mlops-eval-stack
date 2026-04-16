import time

from dagster import ConfigurableResource
from openai import OpenAI


class VLLMResource(ConfigurableResource):
    base_url: str
    model_name: str
    
    def complete(self, prompt: str) -> dict:
        base_url = self.base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        client = OpenAI(base_url=base_url, api_key="dummy")
        t0 = time.perf_counter()
        response = client.completions.create(
            model=self.model_name,
            prompt=prompt,
            max_tokens=256,
        )
        ttft = time.perf_counter() - t0  # proxy for TTFT
        return {
            "text": response.choices[0].text,
            "ttft_s": round(ttft, 4),
            "tokens": response.usage.completion_tokens,
        }