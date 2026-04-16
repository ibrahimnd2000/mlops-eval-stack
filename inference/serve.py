"""Launch vLLM with a localtunnel public URL — intended for Colab GPU environments."""
import argparse
import os
import re
import subprocess
import sys
import time


def _localtunnel(port: int, timeout: int = 30) -> str:
    """Start a localtunnel process and return the public HTTPS URL."""
    lt = subprocess.Popen(
        ["lt", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = lt.stdout.readline()
        if not line:
            time.sleep(0.2)
            continue
        match = re.search(r"https?://\S+", line)
        if match:
            return match.group(0)
    raise RuntimeError(f"localtunnel did not print a URL within {timeout}s")


def launch(model: str = "Qwen/Qwen2.5-1.5B-Instruct", port: int = 8000) -> str:
    """Start vLLM server and return the public URL (localtunnel) or local URL."""
    subprocess.Popen([
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", model,
        "--host", "0.0.0.0",
        "--port", str(port),
    ])

    try:
        public_url = _localtunnel(port)
        print(f"vLLM public URL: {public_url}")
        return public_url
    except FileNotFoundError:
        local_url = f"http://localhost:{port}"
        print(f"localtunnel (lt) not found — server at {local_url}")
        print("Install with: npm install -g localtunnel")
        return local_url


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("VLLM_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct"))
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    launch(model=args.model, port=args.port)
