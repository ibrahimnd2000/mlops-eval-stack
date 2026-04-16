FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

# Install dependencies first — this layer is cached unless pyproject.toml/uv.lock change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy source code
COPY dagster_pipelines/ ./dagster_pipelines/
COPY eval_harness/ ./eval_harness/
COPY inference/ ./inference/
COPY storage/ ./storage/
COPY dagster.yaml workspace.yaml ./

# DuckDB + Parquet files live here at runtime
RUN mkdir -p storage

# Dagster reads instance config from DAGSTER_HOME
ENV DAGSTER_HOME=/app
