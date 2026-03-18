# Entmoot

Domain-aware entity and fact knowledge graph.

Stores **entities** (alternatives), **attributes** (spec dimensions), and **canonical facts**
(sourced values with full provenance) for use by [Decider](https://github.com/brightwater-ss/decider)
and other decision tools.

## Quick start

```bash
uv sync --extra dev
cp .env.example .env   # edit credentials if needed

# Start FalkorDB
docker run --name entmoot-falkordb -p 6379:6379 falkordb/falkordb

# Run dev server
uv run uvicorn entmoot.app:app --reload --port 7000
```

API runs at `http://localhost:7000`. See `docs/prd/` for feature specs.

## Running tests

```bash
# Health test — no database needed
uv run pytest tests/test_health.py

# Full suite — requires FalkorDB running (see above)
uv run pytest
```
