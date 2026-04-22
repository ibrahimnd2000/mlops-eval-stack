# mlops-eval-stack

End-to-end LLM evaluation pipeline using **Dagster**, **vLLM**, **lm-eval-harness**, **DuckDB**, and **MLflow**. Covers both text and vision-language models in a single orchestrated stack: inference and orchestration are separate concerns, results are versioned in a queryable store, and every pipeline run is tracked in MLflow.

## Architecture

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                          Dagster workspace                               │
  │                                                                          │
  │  Text pipeline (eval_job)                                                │
  │  ┌─────────────┐   ┌─────────────┐   ┌──────────┐                       │
  │  │ eval_results│──▶│ score_table │──▶│dashboard │                       │
  │  │ (lm-eval)   │   │ (DuckDB +   │   │ (HTML)   │                       │
  │  └─────────────┘   │  Parquet)   │   └──────────┘                       │
  │                    └─────────────┘                                       │
  │  Multimodal pipeline (multimodal_eval_job)                               │
  │  ┌──────────────────┐   ┌────────────────────┐                           │
  │  │pathvqa_eval_     │──▶│multimodal_score_   │                           │
  │  │results (LLaVA)   │   │table (DuckDB)      │                           │
  │  └──────────────────┘   └────────────────────┘                           │
  │                                                                          │
  │  Registry pipeline (registry_job)                                        │
  │  ┌──────────────────────────────┐                                        │
  │  │ model_registry_entry         │──▶ MLflow (port 5001)                  │
  │  │ (logs all metrics to MLflow) │                                        │
  │  └──────────────────────────────┘                                        │
  │                                                                          │
  │  ┌──────────────────────────┐                                            │
  │  │  Sensor (new_checkpoint) │                                            │
  │  │  Polls checkpoints/      │                                            │
  │  │  Triggers eval_job       │                                            │
  │  └──────────────────────────┘                                            │
  └─────────────────────────────────────────────────────────────────────────┘
         ▲                        ▲
  ┌──────┴──────┐          ┌──────┴──────┐
  │ vLLM text   │          │ vLLM vision │
  │ port 8000   │          │ port 8001   │
  │ Qwen 2.5-   │          │ LLaVA-1.5- │
  │ 1.5B        │          │ 7B          │
  └─────────────┘          └─────────────┘
```

## What it demonstrates

- **Software-defined assets** — three independent pipelines with explicit upstream/downstream dependencies visible in the Dagster UI
- **Text benchmarking** — `eval_results` runs ARC-Easy and HellaSwag via lm-eval-harness against a vLLM OpenAI-compatible endpoint
- **Vision-language evaluation** — `pathvqa_eval_results` evaluates LLaVA-1.5-7B on PathVQA yes/no questions using HuggingFace streaming to avoid OOM on the 32k-image dataset
- **MLflow experiment tracking** — `model_registry_entry` logs all text and vision metrics to an MLflow file-store, viewable in the MLflow UI
- **Configurable inference resources** — swap text or vision endpoints via env vars; no code changes needed
- **Token-level observability** — `TokenObserver` records per-request TTFT and throughput; p50/p95/p99 latency percentiles are stored alongside benchmark scores
- **Sensor-triggered runs** — dropping a `.bin` checkpoint into `checkpoints/` automatically triggers the text eval pipeline
- **Dockerised** — all services (webserver, daemon, Postgres, MLflow) run via `docker compose up`

## Project structure

```
mlops-eval-stack/
├── dagster_pipelines/
│   ├── __init__.py               # Definitions — assets, resources, jobs, sensor
│   ├── assets/
│   │   ├── eval_run.py           # Runs lm-eval-harness against vLLM (text)
│   │   ├── score_table.py        # Normalises scores + token metrics → DuckDB + Parquet
│   │   ├── dashboard.py          # Writes storage/dashboard.html
│   │   ├── mllm_eval_run.py      # PathVQA yes/no eval via LLaVA-1.5-7B
│   │   ├── multimodal_score_table.py  # Persists PathVQA accuracy → DuckDB
│   │   └── mlflow_registry.py    # Logs all metrics to MLflow
│   ├── resources/
│   │   ├── vllm_client.py        # ConfigurableResource for text vLLM endpoint
│   │   └── vllm_multimodal_client.py  # ConfigurableResource for vision vLLM endpoint
│   └── sensors.py                # Watches checkpoints/ for new .bin files
├── eval_harness/
│   └── runner.py                 # lm_eval.simple_evaluate wrapper + latency probe
├── inference/
│   ├── serve.py                  # Launches vLLM + localtunnel (Colab)
│   └── observer.py               # TokenObserver — writes JSONL per request
├── storage/                      # Runtime artefacts (DuckDB, Parquet, MLflow runs)
│   └── db.py                     # Schema definitions and DuckDB connection helper
├── notebooks/
│   └── colab_setup.ipynb         # Phase 1 (Qwen text) + Phase 2 (LLaVA vision) setup
├── Dockerfile
├── docker-compose.yml
├── docker-compose.override.yml   # Dev bind mounts (source code + storage)
└── dagster.yaml
```

## Quickstart — Docker

```bash
git clone https://github.com/ibrahimnd2000/mlops-eval-stack
cd mlops-eval-stack

cp .env.example .env
# Edit .env: set VLLM_BASE_URL and VLLM_MULTIMODAL_BASE_URL to your tunnel URLs

docker compose up --build
```

| Service | URL | Role |
|---------|-----|------|
| `dagster-webserver` | http://localhost:3000 | Asset graph UI, manual job triggers |
| `mlflow` | http://localhost:5001 | Experiment tracking and metric history |
| `postgres` | port 5432 | Dagster run history and event log storage |

DuckDB files, Parquet snapshots, `dashboard.html`, and MLflow runs are persisted on the `eval_storage` named volume. In dev, `docker-compose.override.yml` bind-mounts `./storage` so files are visible directly on disk.

## Quickstart — local dev

```bash
pip install uv
uv sync

dagster dev -m dagster_pipelines
```

Override endpoints in the Dagster UI launchpad or set `VLLM_BASE_URL` / `VLLM_MULTIMODAL_BASE_URL` in your shell before running.

## Running inference on Colab

Open `notebooks/colab_setup.ipynb` in Google Colab with a GPU runtime. The notebook is split into two phases.

**Phase 1 — Qwen 2.5-1.5B text model (port 8000)**

1. Installs vLLM and dependencies
2. Starts the vLLM server in a detached process (survives kernel restarts)
3. Opens a localtunnel and prints the public URL

Paste that URL as `VLLM_BASE_URL`.

**Phase 2 — LLaVA-1.5-7B vision model (port 8001)**

1. Installs vision-language dependencies
2. Starts a second vLLM server for LLaVA-1.5-7B
3. Polls until the server is healthy (up to 6 minutes for model download)
4. Smoke-tests the vision endpoint with a locally generated PIL image
5. Opens a localtunnel on port 8001 and prints the public URL

Paste that URL as `VLLM_MULTIMODAL_BASE_URL`.

## Jobs

| Job | Assets | Trigger |
|-----|--------|---------|
| `eval_job` | `eval_results → score_table → dashboard` | Sensor (new checkpoint) or manual |
| `multimodal_eval_job` | `pathvqa_eval_results → multimodal_score_table` | Manual |
| `registry_job` | `model_registry_entry` | Manual (after both eval jobs complete) |

Run any job manually from the Dagster UI at http://localhost:3000 → **Jobs**.

## MLflow

After `registry_job` completes, open http://localhost:5001 and select the `kaiko-eval-stack` experiment to see:

- `arc_easy/acc_none`, `arc_easy/acc_norm_none` — ARC-Easy accuracy scores
- `hellaswag/acc_none`, `hellaswag/acc_norm_none` — HellaSwag accuracy scores
- `pathvqa/yn_accuracy` — PathVQA yes/no binary accuracy
- Params: `text_model`, `vision_model`, `pathvqa_samples`

> **Note:** MLflow is pinned to `2.19.0` in `pyproject.toml` to match the Docker image. If the `./storage/mlruns/` directory contains data written by a different MLflow version, delete it before starting the MLflow service: `rm -rf storage/mlruns/`

## Querying results

```python
import duckdb

con = duckdb.connect("storage/eval_scores.duckdb")

# Latest text benchmark scores
con.execute("""
    SELECT run_id, task, metric, value, ran_at
    FROM scores
    ORDER BY ran_at DESC
    LIMIT 20
""").df()

# PathVQA accuracy history
con.execute("""
    SELECT run_id, benchmark, metric, value, samples_evaluated, ran_at
    FROM multimodal_scores
    ORDER BY ran_at DESC
""").df()

# Latency percentiles
con.execute("""
    SELECT metric, ROUND(value * 1000, 2) AS ms, computed_at
    FROM latency_reports
    ORDER BY computed_at DESC
""").df()
```

Or open `storage/dashboard.html` in a browser after any pipeline run for a rendered view of all three tables.

## Sensor — triggering on new checkpoints

Drop a `.bin` file into `checkpoints/` and `new_checkpoint_sensor` (polling every 30 s) will automatically trigger `eval_job`:

```bash
cp my_finetuned_model.bin checkpoints/
# → sensor fires → eval_results → score_table → dashboard
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_BASE_URL` | `http://localhost:8000` | vLLM text endpoint (Qwen) |
| `VLLM_MODEL_NAME` | `Qwen/Qwen2.5-1.5B-Instruct` | Text model name |
| `VLLM_MULTIMODAL_BASE_URL` | `http://localhost:8001` | vLLM vision endpoint (LLaVA) |
| `VLLM_MULTIMODAL_MODEL_NAME` | `llava-hf/llava-1.5-7b-hf` | Vision model name |
| `DAGSTER_POSTGRES_URL` | `postgresql://dagster:dagster@postgres/dagster` | Dagster state DB (Docker only) |

Copy `.env.example` to `.env` and fill in the tunnel URLs from Colab before running `docker compose up`.

## Tech stack

| Component | Library / Tool |
|-----------|---------------|
| Orchestration | [Dagster](https://dagster.io) 1.13+ |
| Text inference server | [vLLM](https://github.com/vllm-project/vllm) |
| Vision inference server | [vLLM](https://github.com/vllm-project/vllm) + LLaVA-1.5-7B |
| Text benchmark harness | [lm-eval-harness](https://github.com/EleutherAI/lm-evaluation-harness) |
| Vision benchmark dataset | [PathVQA](https://huggingface.co/datasets/flaviagiammarino/path-vqa) via HuggingFace Datasets |
| Experiment tracking | [MLflow](https://mlflow.org) 2.19.0 |
| Results store | [DuckDB](https://duckdb.org) |
| Orchestration state | PostgreSQL (Docker) / SQLite (local dev) |
| Tunnel (Colab) | [localtunnel](https://github.com/localtunnel/localtunnel) |
