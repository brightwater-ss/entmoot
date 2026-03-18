# Entmoot — Claude Code conventions

## Project overview

Entmoot is a domain-aware entity and fact knowledge graph.
It stores entities (alternatives), attributes (spec dimensions), and canonical facts
(sourced values) for use by Decider and other decision tools.

## Repo structure

```
src/
  entmoot/
    app.py         Litestar application entry point; create_app() factory
    config.py      Settings from environment variables (pydantic-settings)
    guards.py      Litestar guards (admin API key check)
    routes/        Route handlers, one file per resource
    graph/         FalkorDB driver, AsyncGraph wrapper, schema init
    pipeline/      Ingestion workers: scraper, ETL, AI extraction
    models/        Pydantic request/response models
tests/
docs/
  adr/             Architecture Decision Records
  prd/             Product Requirements Documents
CHANGELOG.md
```

## Tech stack

| Layer | Tech |
|---|---|
| Language | Python 3.12+, uv |
| Framework | Litestar 2 |
| Graph DB | FalkorDB (server via Docker; FalkorDBLite for embedded — planned) |
| Driver | `falkordb` Python package (`falkordb.asyncio` for async) |
| Validation | Pydantic v2 |
| HTTP client | httpx |
| Linting | Ruff |
| Tests | pytest, pytest-asyncio |

## Development

```bash
# Install dependencies
uv sync --extra dev

# Copy and edit environment
cp .env.example .env

# Start FalkorDB
docker run --name entmoot-falkordb -p 6379:6379 falkordb/falkordb

# Run dev server
uv run uvicorn entmoot.app:app --reload --port 7000

# Lint
uv run ruff check src/

# Test (health test runs without DB; others require FalkorDB)
uv run pytest
```

## Graph access pattern

All routes access the graph via `request.app.state.graph` (an `AsyncGraph` instance).
Do not import the driver or graph globals directly in route handlers.
In tests, inject the graph via the `client` fixture in `conftest.py`.

## Code conventions

- Type annotations required on all function signatures
- Ruff for linting (`uv run ruff check`)
- `src` layout (`src/entmoot/`)
- Test files in `tests/`, named `test_*.py`
- Named exports only — avoid star imports

## Documentation

- **ADR**: Write one for any significant architectural decision. Use `docs/adr/NNN-title.md`.
  Update `docs/adr/README.md` index. Status: `proposed → accepted → deprecated`.
- **PRD**: Write one per feature. Use `docs/prd/NNN-feature.md`.
  Update `docs/prd/README.md` index. Status: `draft → approved → shipped`.
- **CHANGELOG**: Update `CHANGELOG.md` with every user-visible change under `[Unreleased]`.

## Git

- Branch naming: `feat/short-description`, `fix/short-description`, `chore/short-description`
- Commit messages: imperative present tense (`Add entity search route`, not `Added...`)
- Every PR must update `CHANGELOG.md` under `[Unreleased]`
