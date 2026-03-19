# ADR-002: Pipeline Orchestration with Dagster and Adapter Pattern

**Status:** accepted
**Date:** 2026-03-18

## Context

Entmoot's ingestion pipelines (Wikidata import, future web scrapers, AI
extraction, dedup review) need:

1. **Scheduled execution** — nightly cron-style imports
2. **Multi-step ETL** — scrape → extract → deduplicate → load as distinct
   retryable steps
3. **AI extraction** — LLM calls as pipeline stages
4. **Human-in-the-loop** — pause for admin review before downstream work
   (e.g. dedup resolution)
5. **Observability** — step-level status, run history, retries visible in a UI

Running pipeline logic inline inside HTTP request handlers (the prior approach)
does not satisfy requirements 1, 2, 4, or 5.

## Options Considered

| Option | Pros | Cons |
|---|---|---|
| **Dagster** | Asset-oriented (fits knowledge graph lineage), Apache 2.0, full UI, Python-native, async assets, human-in-the-loop via asset checks | Heavier setup than Prefect |
| **Prefect** | Very simple to start, Python decorators, good UI, cron support | Asset model is secondary; lineage less first-class |
| **Temporal** | Best-in-class durable execution and human-in-the-loop signals | Requires Go server; overkill at this stage |
| **Plain cron + scripts** | Zero overhead | No observability, retry, or H-I-T-L |

## Decision

**Dagster** is adopted as the pipeline orchestrator.

Dagster's *software-defined asset* model maps naturally onto Entmoot's data
model: imported entities, attributes, and values are assets that are computed
from source data. Asset lineage in the Dagster UI gives immediate insight into
what data was produced from which source run.

**Adapter pattern** is used to ensure Dagster remains a swappable detail:

```
PipelineRunner (typing.Protocol)
  ├── NullPipelineRunner  — in-process, synchronous; zero extra deps
  └── DagsterPipelineRunner  — optional; requires `uv sync --extra dagster`
```

Routes and tests depend only on `PipelineRunner`. Neither implementation is
imported directly outside of the bootstrap layer (`app.py`). The active
implementation is selected at startup via `PIPELINE_RUNNER` env var.

Dagster is an **optional dependency** (`[project.optional-dependencies] dagster`
in `pyproject.toml`). The default runner is `NullPipelineRunner` — the app
starts and all existing tests pass without Dagster installed.

## Consequences

- `POST /admin/import/wikidata` now returns a `PipelineRun` (run_id + status)
  rather than `WikidataImportResult` directly. With `NullPipelineRunner`,
  `status` is always `"success"` and `result` is populated inline. With
  `DagsterPipelineRunner`, `status` may be `"pending"`.
- `GET /admin/pipelines/runs/{run_id}` allows polling for async run status.
- Core pipeline classes (`WikidataImporter`, future scrapers/extractors) have
  **no Dagster dependency** — they are plain async Python. Dagster assets are
  thin wrappers in `entmoot.pipeline.dagster.assets`.
- Adding a new pipeline requires: (1) implement core logic in `pipeline/`,
  (2) register a handler in `app.py` for `NullPipelineRunner`, (3) add a
  Dagster `@asset` in `pipeline/dagster/assets.py`.
- Swapping Dagster for another orchestrator (Prefect, Temporal) requires only
  replacing the `pipeline/dagster/` package and updating `app.py`'s
  `_build_runner()`. The protocol, routes, and core logic are unchanged.

## Running Dagster locally

```bash
uv sync --extra dagster
dagster dev          # UI at http://localhost:3000
dagster asset list   # confirms wikidata_import is registered
```

To use the Dagster runner with the Litestar API:

```bash
PIPELINE_RUNNER=dagster uv run uvicorn entmoot.app:app --port 7001
```
