"""Launch vLLM with an optional ngrok tunnel — intended for Colab GPU environments."""
import argparse
import subprocess
import sys


def launch(model: str = "Qwen/Qwen2.5-1.5B-Instruct", port: int = 8000) -> str:
    """Start vLLM server and return the public URL (ngrok) or local URL."""
    subprocess.Popen([
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", model,
        "--host", "0.0.0.0",
        "--port", str(port),
    ])

    try:
        from pyngrok import ngrok
        tunnel = ngrok.connect(port)
        public_url: str = tunnel.public_url
        print(f"vLLM public URL: {public_url}")
        return public_url
    except ImportError:
        local_url = f"http://localhost:{port}"
        print(f"pyngrok not installed — server at {local_url}")
        return local_url


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    launch(model=args.model, port=args.port)
