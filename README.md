# Entmoot

Domain-aware entity and fact knowledge graph.

Stores **entities** (alternatives), **attributes** (spec dimensions), and **canonical facts**
(sourced values with full provenance) for use by [Decider](https://github.com/brightwater-ss/decider)
and other decision tools.

## Quick start

```bash
uv sync --extra dev
cp .env.example .env   # edit Neo4j credentials

# Start Neo4j
docker run --name entmoot-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/changeme \
  neo4j:community

# Run dev server
uv run uvicorn entmoot.app:app --reload --port 7000
```

API runs at `http://localhost:7000`. See `docs/prd/` for feature specs.
