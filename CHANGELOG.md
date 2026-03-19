# Changelog

All notable changes to Entmoot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- ADR-001: graph schema design (nodes, relationships, constraints, indexes)
- `config.py`: env-based settings via pydantic-settings
- `graph/driver.py`: async FalkorDB driver with init/close lifecycle
- `graph/schema.py`: constraint and full-text index creation on startup
- Pydantic response models: `Entity`, `Attribute`, `Value`, `Domain`, `ValueGroup`
- `GET /entities` — search entities by name (full-text) with optional domain filter
- `GET /entities/:id` — get entity with all values grouped by attribute, conflict-flagged
- `GET /attributes` — search attributes by name with optional domain filter
- `GET /attributes/:id` — get attribute detail
- `POST /admin/domains` — seed a domain (admin key required)
- `POST /admin/entities` — seed an entity with domain links (admin key required)
- `POST /admin/attributes` — seed an attribute with domain links (admin key required)
- `POST /admin/values` — seed a value for an (entity, attribute) pair (admin key required)
- `POST /admin/import/wikidata` — bulk import entities and values from Wikidata by class or Q-ID list (admin key required)
- `WikidataImporter` pipeline class in `entmoot.pipeline.wikidata`
- Standalone import script: `uv run python -m entmoot.pipeline.import_wikidata`
- Admin guard: `X-Admin-Key` header checked against `ADMIN_API_KEY` env var
- `create_app(connect_db)` factory for test isolation
- Tests: health (no DB), schema idempotency, admin seed + conflict detection, guard rejection
- PRD-001: Wikidata Import Pipeline

### Changed
- Replaced Neo4j with FalkorDB per ADR-005; uses native async client (`falkordb.asyncio`)
- Graph driver rewritten as `AsyncGraph` wrapper around `falkordb.asyncio.Graph`
- Schema init uses FalkorDB Python API (`create_node_unique_constraint`, `create_node_fulltext_index`)
- Config vars renamed from `NEO4J_*` to `FALKORDB_*`; default port 6379
- Integration tests skip gracefully when FalkorDB server is unavailable
- `Fact` renamed to `Value` throughout (node label, models, routes, API); "fact" implies
  truth, "value" is neutral about provenance and verification status
