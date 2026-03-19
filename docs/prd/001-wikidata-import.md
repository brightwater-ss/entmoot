# PRD-001: Wikidata Import Pipeline

**Status:** approved
**Date:** 2026-03-18

## Goal

Enable admins to bulk-import entities and values from Wikidata into the Entmoot
knowledge graph, both via the HTTP admin API and a standalone CLI script.

## Background

Entmoot's admin API supports manual seeding one record at a time. Populating the
graph for real use requires bulk import from a trusted external source. Wikidata
maps naturally onto Entmoot's data model:

| Wikidata | Entmoot |
|---|---|
| Item (Q-number) | Entity |
| Property (P-number) | Attribute |
| Statement | Value (`source_type="scraped"`) |

## Scope

### In scope

- Import entities by Wikidata class (e.g. Q4830453 = business enterprise)
- Import entities by explicit Q-ID list
- Import values for specified properties (P-IDs) alongside entities
- Idempotent entity and attribute import: re-running skips already-imported records
  (matched by `wikidata_id` node property)
- Graceful handling of non-English items (skipped with non-fatal error)
- Filtering of non-string property values (item references, coordinates, etc.)
  at SPARQL level; residual URI values filtered in Python
- Class imports capped at 1000 items per class (prevents runaway queries on
  large classes like Q5 = human)
- `--dry-run` mode: resolves IDs and fetches labels without writing to graph
- Admin guard (`X-Admin-Key`) applies to the HTTP endpoint automatically

### Out of scope

- Automatic periodic re-sync with Wikidata
- Importing Wikidata item descriptions (no corresponding Entmoot field)
- Importing item-reference property values (e.g. P31 → Q4830453)
- Wikidata OAuth / authenticated SPARQL requests
- Value deduplication (values are append-only per ADR-001)

## Acceptance Criteria

1. `POST /admin/import/wikidata` accepts `class_ids`, `item_ids`, `property_ids`,
   `domain_slugs` and returns `WikidataImportResult` with counts.
2. Re-running the same import does not create duplicate entities or attributes.
3. Items without an English label are skipped and logged in `result.errors`.
4. Non-string property values (item URIs, quantities) are excluded from values.
5. `uv run python -m entmoot.pipeline.import_wikidata --help` works.
6. `--dry-run` prints resolved entities without writing to FalkorDB.
7. `WikidataImporter` is independently importable for use in other scripts.

## HTTP API

```
POST /admin/import/wikidata
X-Admin-Key: <key>

{
  "class_ids": ["Q4830453"],        // optional
  "item_ids": ["Q95", "Q37156"],    // optional (at least one of class_ids/item_ids required)
  "property_ids": ["P571", "P159"], // optional; empty = skip value import
  "domain_slugs": ["cloud-providers"]
}

→ 201
{
  "entities_created": 3,
  "entities_skipped": 0,
  "attributes_created": 2,
  "attributes_skipped": 0,
  "values_created": 5,
  "errors": []
}
```

## CLI

```
uv run python -m entmoot.pipeline.import_wikidata \
  --items Q95 Q37156 \
  --props P571 P159 \
  --domains cloud-providers

uv run python -m entmoot.pipeline.import_wikidata \
  --class Q4830453 --domains companies --dry-run
```
