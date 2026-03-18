# Entmoot — Claude Code conventions

## Project overview

Entmoot is a domain-aware entity and fact knowledge graph.
It stores entities (alternatives), attributes (spec dimensions), and canonical facts
(sourced values) for use by Decider and other decision tools.

## Repo structure

```
src/
  entmoot/
    app.py         Litestar application entry point
    routes/        Route handlers, one file per resource
    graph/         Neo4j driver, query helpers, schema init
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
| Graph DB | Neo4j (Community Edition for dev; Aura for cloud) |
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

# Run dev server (requires Neo4j running locally or via Docker)
uv run uvicorn entmoot.app:app --reload --port 7000

# Lint
uv run ruff check src/

# Test
uv run pytest
```

## Neo4j local setup

```bash
docker run \
  --name entmoot-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/changeme \
  neo4j:community
```

## Code conventions

- Type annotations required on all function signatures
- Ruff for linting (`uv run ruff check`)
- `src` layout (`src/entmoot/`)
- Test files in `tests/`, named `test_*.py`
- Named exports only — avoid star imports
- No default exports

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
