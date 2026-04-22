import base64
import time

from dagster import ConfigurableResource
from openai import OpenAI


class VLLMMultimodalResource(ConfigurableResource):
    base_url: str
    model_name: str

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def complete_with_image(self, prompt: str, image_path: str) -> dict:
        base_url = self.base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        client = OpenAI(base_url=base_url, api_key="dummy")
        t0 = time.perf_counter()
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{self._encode_image(image_path)}"
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=64,
        )
        elapsed = time.perf_counter() - t0
        return {
            "text": response.choices[0].message.content,
            "ttft_s": round(elapsed, 4),
            "tokens": response.usage.completion_tokens,
        }
