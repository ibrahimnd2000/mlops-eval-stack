# mlops-eval-stack

End-to-end LLM evaluation pipeline using **Dagster**, **vLLM**, **lm-eval-harness**, and **DuckDB**. Designed to mirror the architecture used in production MLOps stacks: orchestration and inference are separate concerns, results are versioned in a queryable store, and the whole pipeline is sensor-triggered on new model checkpoints.

## Architecture

```
                  ┌─────────────────────────────────────────────────────┐
                  │               Dagster workspace                      │
  ┌─────────────┐ │  ┌─────────────┐   ┌─────────────┐   ┌──────────┐  │
  │  vLLM       │ │  │ eval_results│   │ score_table │   │dashboard │  │
  │  server     │──▶  │ (lm-eval)   │──▶│ (normalise  │──▶│ (HTML)   │  │
  │  (OpenAI    │ │  │             │   │  + store)   │   │          │  │
  │   compat)   │ │  └─────────────┘   └──────┬──────┘   └──────────┘  │
  │             │ │                           │                         │
  │  Token      │ │                    ┌──────▼──────────────────┐      │
  │  observer   │──▶                   │ DuckDB (scores +        │      │
  │  (TTFT/TPS) │ │                    │ latency_reports tables) │      │
  └─────────────┘ │                    │ + Parquet snapshots     │      │
        ▲         │                    └─────────────────────────┘      │
        │         │                                                      │
  ┌─────┴───────┐ │  ┌──────────────────────────┐                       │
  │  Model      │ │  │  Sensor (new_checkpoint)  │                       │
  │  checkpoint │ │  │  Polls checkpoints/       │                       │
  │  (.bin)     │ │  │  Triggers full asset run  │                       │
  └─────────────┘ │  └──────────────────────────┘                       │
                  └─────────────────────────────────────────────────────┘
```

## What it demonstrates

- **Software-defined assets** — `eval_results → score_table → dashboard` with explicit upstream/downstream dependencies visible in the Dagster UI
- **Configurable inference resource** — swap the vLLM endpoint (local, Colab, cloud) via `VLLM_BASE_URL`; no code changes needed
- **Token-level observability** — `TokenObserver` records per-request TTFT and throughput; `score_table` computes p50/p95/p99 and stores them alongside benchmark accuracy in the same DuckDB run
- **Sensor-triggered runs** — dropping a `.bin` checkpoint into `checkpoints/` automatically triggers a full eval pipeline run
- **Parquet export** — every run snapshots `scores.parquet` and `latency_reports.parquet` for offline analysis
- **Dockerised** — webserver, daemon, and Postgres (Dagster state) run via `docker compose up`

## Project structure

```
mlops-eval-stack/
├── dagster_pipelines/
│   ├── __init__.py          # Definitions — assets, resource, job, sensor
│   ├── assets/
│   │   ├── eval_run.py      # Runs lm-eval-harness against vLLM
│   │   ├── score_table.py   # Normalises scores + token metrics → DuckDB + Parquet
│   │   └── dashboard.py     # Writes storage/dashboard.html
│   ├── resources/
│   │   └── vllm_client.py   # ConfigurableResource wrapping the OpenAI-compat API
│   └── sensors.py           # Watches checkpoints/ for new .bin files
├── eval_harness/
│   └── runner.py            # Thin wrapper around lm_eval.simple_evaluate
├── inference/
│   ├── serve.py             # Launches vLLM + optional ngrok tunnel (Colab)
│   └── observer.py          # TokenObserver — writes JSONL per request
├── storage/                 # Runtime artefacts (DuckDB, Parquet, dashboard.html)
├── notebooks/
│   └── colab_setup.ipynb    # GPU environment bootstrap
├── Dockerfile
├── docker-compose.yml
└── dagster.yaml
```

## Quickstart — Docker

```bash
# Clone and build
git clone https://github.com/mibrahim2000/mlops-eval-stack
cd mlops-eval-stack

# Point at your vLLM endpoint (ngrok URL from Colab, or local)
export VLLM_BASE_URL=https://your-ngrok-url.ngrok.io

docker compose up --build
```

Dagster UI is available at **http://localhost:3000**.

Services:

| Service | Role |
|---------|------|
| `postgres` | Dagster run history and event log storage |
| `dagster-webserver` | Asset graph UI on port 3000 |
| `dagster-daemon` | Sensor polling and backfill execution |

DuckDB files, Parquet snapshots, and `dashboard.html` are persisted on the `eval_storage` named volume.

## Quickstart — local dev

```bash
# Install dependencies
pip install uv
uv sync

# Start the Dagster UI (uses ~/.dagster SQLite — no Postgres needed)
dagster dev -m dagster_pipelines
```

Override the vLLM endpoint in `dagster_pipelines/__init__.py` or set resources in the Dagster UI launchpad.

## Running inference on Colab

Open `notebooks/colab_setup.ipynb` in Google Colab (GPU runtime). The notebook:

1. Installs vLLM and dependencies
2. Starts the vLLM OpenAI-compatible server on port 8000
3. Creates an ngrok tunnel and prints the public URL

Paste the public URL as `VLLM_BASE_URL` when starting the stack.

```python
# notebooks/colab_setup.ipynb — key cells
!pip install vllm pyngrok

from inference.serve import launch
public_url = launch(model="Qwen/Qwen2.5-1.5B-Instruct", port=8000)
print(public_url)  # e.g. https://abc123.ngrok.io
```

## Recording token metrics

Wrap your vLLM calls with `TokenObserver` to populate the latency tables:

```python
from inference.observer import TokenObserver

obs = TokenObserver()
obs.record(
    prompt_tokens=128,
    completion_tokens=64,
    ttft_s=0.18,
    total_s=1.2,
    model="Qwen/Qwen2.5-1.5B-Instruct",
)
```

Each `score_table` asset run reads `storage/token_metrics.jsonl` and writes p50/p95/p99 TTFT and throughput percentiles into DuckDB alongside the benchmark scores.

## Querying results

```python
import duckdb

con = duckdb.connect("storage/eval_scores.duckdb")

# Latest benchmark scores per task
con.execute("""
    SELECT run_id, task, metric, value
    FROM scores
    ORDER BY ran_at DESC
    LIMIT 20
""").df()

# Latency trend
con.execute("""
    SELECT metric, ROUND(value * 1000, 2) AS ms, computed_at
    FROM latency_reports
    ORDER BY computed_at DESC
""").df()
```

Or open `storage/dashboard.html` in a browser for a rendered view after any pipeline run.

## Sensor — triggering on new checkpoints

Drop a `.bin` file into `checkpoints/` and the `new_checkpoint_sensor` (polling every 30 s) will automatically trigger a full pipeline run with that checkpoint as the model:

```bash
cp my_finetuned_model.bin checkpoints/
# → sensor fires → eval_results → score_table → dashboard
```

## Tech stack

| Component | Library / Tool |
|-----------|---------------|
| Orchestration | [Dagster](https://dagster.io) 1.13+ |
| Inference server | [vLLM](https://github.com/vllm-project/vllm) |
| Benchmark harness | [lm-eval-harness](https://github.com/EleutherAI/lm-evaluation-harness) |
| Results store | [DuckDB](https://duckdb.org) |
| Orchestration state | PostgreSQL (Docker) / SQLite (local dev) |
| Tunnel (Colab) | [pyngrok](https://github.com/alexdlaird/pyngrok) |
