import json
import time
from pathlib import Path


_DEFAULT_LOG = Path(__file__).resolve().parent.parent / "storage" / "token_metrics.jsonl"


class TokenObserver:
    def __init__(self, log_path: Path | str = _DEFAULT_LOG):
        self.log_path = Path(log_path)
    
    def record(self, prompt_tokens: int, completion_tokens: int,
               ttft_s: float, total_s: float, model: str):
        record = {
            "ts": time.time(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "ttft_s": round(ttft_s, 4),
            "throughput_tps": round(completion_tokens / total_s, 1),
            "total_s": round(total_s, 4),
        }
        with self.log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")