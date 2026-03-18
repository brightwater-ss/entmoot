# Changelog

All notable changes to Entmoot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- ADR-001: graph schema design (nodes, relationships, constraints, indexes)
- `config.py`: env-based settings via pydantic-settings
- `graph/driver.py`: async Neo4j driver with init/close lifecycle
- `graph/schema.py`: constraint and full-text index creation on startup
- Pydantic response models: `Entity`, `Attribute`, `Fact`, `Domain`, `FactGroup`
- `GET /entities` — search entities by name (full-text) with optional domain filter
- `GET /entities/:id` — get entity with all facts grouped by attribute, conflict-flagged
- `GET /attributes` — search attributes by name with optional domain filter
- `GET /attributes/:id` — get attribute detail
- `POST /admin/domains` — seed a domain (admin key required)
- `POST /admin/entities` — seed an entity with domain links (admin key required)
- `POST /admin/attributes` — seed an attribute with domain links (admin key required)
- `POST /admin/facts` — seed a fact for an (entity, attribute) pair (admin key required)
- Admin guard: `X-Admin-Key` header checked against `ADMIN_API_KEY` env var
- `create_app(connect_db)` factory for test isolation
- Tests: health (no DB), schema idempotency, admin seed + conflict detection, guard rejection
