# ADR-001: Graph Schema Design

**Status:** accepted
**Date:** 2026-03-18

## Context

Entmoot stores entities, attributes, and facts in a graph database (Neo4j, per ADR-005 in
the Decider repo). This ADR defines the node types, relationship types, and schema constraints,
and records the reasoning behind key design decisions.

## Node Types

### Entity
A named, deduplicated thing that can be an alternative in a decision.

Properties:
- `id` — UUID (unique constraint)
- `name` — canonical display name
- `aliases` — list of alternative names used for deduplication
- `visibility` — `public | org-private`
- `org_id` — nullable; set when `visibility = org-private`
- `created_at`, `updated_at` — ISO 8601 timestamps

### Attribute
A named dimension along which an entity can be described. Analogous to a Wikidata property.

Properties:
- `id` — UUID (unique constraint)
- `name` — canonical display name
- `description` — nullable; human-readable explanation
- `unit` — nullable; e.g. `mpg`, `%`, `USD/month`
- `visibility` — `public | org-private`
- `created_at` — ISO 8601 timestamp

### Domain
A hierarchical classification node. Admin-controlled to prevent fragmentation.

Properties:
- `id` — UUID (unique constraint)
- `name` — display name (e.g. `Cloud Vendor`)
- `slug` — kebab-case identifier (e.g. `cloud-vendor`, unique constraint)
- `created_at` — ISO 8601 timestamp

### Fact
A sourced value for a specific (Entity, Attribute) pair. Analogous to a Wikidata statement.

Properties:
- `id` — UUID (unique constraint)
- `value` — string representation of the value (numeric, boolean, structured values are
  stored as strings and typed by the Attribute's expected type)
- `source_type` — `org-verified | admin | scraped | ai-extracted | manual`
- `source_url` — nullable; URL of the source document
- `confidence` — float 0.0–1.0
- `visibility` — `public | org-private`
- `org_id` — nullable
- `contributed_at` — ISO 8601 timestamp

### Organization
A named account that can claim entities and submit verified facts.

Properties:
- `id` — UUID (unique constraint)
- `name` — display name
- `slug` — kebab-case identifier (unique constraint)
- `created_at` — ISO 8601 timestamp

### Source
A provenance pointer for a Fact.

Properties:
- `id` — UUID (unique constraint)
- `href` — URL
- `accessed_at` — ISO 8601 timestamp

## Relationship Types

```
(Domain)-[:PARENT_OF]->(Domain)

(Entity)-[:BELONGS_TO]->(Domain)
(Entity)-[:SIMILAR_TO {score: float}]->(Entity)
(Entity)-[:MERGED_INTO]->(Entity)
(Entity)-[:CLAIMED_BY]->(Organization)

(Attribute)-[:APPLICABLE_TO]->(Domain)

(Fact)-[:DESCRIBES]->(Entity)
(Fact)-[:FOR_ATTRIBUTE]->(Attribute)
(Fact)-[:SUBMITTED_BY]->(Organization)   // present only for org-verified facts
(Fact)-[:SOURCED_FROM]->(Source)         // present when a source URL is known
```

## Constraints and Indexes

```cypher
CREATE CONSTRAINT entity_id IF NOT EXISTS
  FOR (n:Entity) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT attribute_id IF NOT EXISTS
  FOR (n:Attribute) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT domain_id IF NOT EXISTS
  FOR (n:Domain) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT domain_slug IF NOT EXISTS
  FOR (n:Domain) REQUIRE n.slug IS UNIQUE;

CREATE CONSTRAINT fact_id IF NOT EXISTS
  FOR (n:Fact) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT org_id IF NOT EXISTS
  FOR (n:Organization) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT org_slug IF NOT EXISTS
  FOR (n:Organization) REQUIRE n.slug IS UNIQUE;

CREATE CONSTRAINT source_id IF NOT EXISTS
  FOR (n:Source) REQUIRE n.id IS UNIQUE;

CREATE FULLTEXT INDEX entitySearch IF NOT EXISTS
  FOR (n:Entity) ON EACH [n.name, n.aliases];

CREATE FULLTEXT INDEX attributeSearch IF NOT EXISTS
  FOR (n:Attribute) ON EACH [n.name];
```

## Key Design Decisions

### Facts are nodes, not relationship properties

**Decision:** `Fact` is a first-class node type, not a property on a relationship between
Entity and Attribute.

**Rationale:** Facts have multiple properties (value, source_type, confidence, contributed_at,
visibility, org_id), their own relationships (SUBMITTED_BY, SOURCED_FROM), and there are
typically multiple facts per (Entity, Attribute) pair. Encoding all of this as relationship
properties would produce a large, flat, hard-to-query structure. A node makes traversal and
filtering natural.

### Facts are append-only

**Decision:** Facts are never updated or deleted. A revised value produces a new Fact node
with a new `contributed_at` timestamp. The old fact is retained.

**Rationale:** Preserves the full history of how a value has changed over time. Supports
conflict detection (two facts with different values for the same pair). Prevents organizations
from silently rewriting history.

### Conflict is computed, not stored

**Decision:** The `conflict` flag returned by the API is computed at query time — it is true
when two or more Facts for the same (Entity, Attribute) pair have differing `value` strings.
It is not stored on any node.

**Rationale:** Storing a computed derived value would require updating it on every new Fact
write, introducing a write-time consistency concern. Computing it at read time is simple and
accurate.

### Domain governance is admin-controlled

**Decision:** Domain nodes can only be created by admins. Users may suggest domains via the
API but cannot create them directly.

**Rationale:** Uncontrolled domain creation leads to fragmentation
(`cloud-vendor`, `Cloud Vendors`, `cloud vendor` as separate nodes). A small controlled
vocabulary of domains is more useful than a large noisy one.

### Organization ownership is non-exclusive

**Decision:** An organization claiming an entity may submit `org-verified` facts, but cannot
suppress, hide, or delete facts contributed by other sources.

**Rationale:** Manufacturers and vendors should be able to provide authoritative data, but
must not be able to prevent community members or researchers from contributing observations
that contradict official positions. All values are shown with their provenance; consumers
decide whom to trust.

## Consequences

- `Fact` nodes accumulate over time; old facts for a given pair are never purged automatically.
  A periodic archival or TTL strategy may be needed at scale, but is deferred.
- Conflict detection adds a minor overhead to fact-returning queries (grouping by attribute
  and checking value diversity). Acceptable at current scale.
- Full-text search quality depends on Neo4j's built-in Lucene analyzer. Custom analyzers
  (stemming, synonym expansion) can be added later without schema changes.
