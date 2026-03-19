"""Wikidata → Entmoot import pipeline.

Maps Wikidata items (Q-numbers) to Entities, Wikidata properties (P-numbers)
to Attributes, and Wikidata statements to Values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from entmoot.graph.driver import AsyncGraph
from entmoot.models.admin import WikidataImportRequest, WikidataImportResult

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "EntmootWikidataImporter/0.1 httpx"
WIKIDATA_ITEM_BASE = "https://www.wikidata.org/wiki/"
WIKIDATA_ENTITY_URI = "http://www.wikidata.org/entity/"
BATCH_SIZE = 50


@dataclass
class _Item:
    q_id: str
    label: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class _Statement:
    q_id: str
    p_id: str
    value: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_id(uri: str) -> str:
    """Extract Q or P ID from a Wikidata URI, e.g. 'http://…/entity/Q95' → 'Q95'."""
    return uri.rstrip("/").rsplit("/", 1)[-1]


def _batches(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


class WikidataImporter:
    def __init__(self, graph: AsyncGraph, http: httpx.AsyncClient) -> None:
        self._graph = graph
        self._http = http

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, req: WikidataImportRequest) -> WikidataImportResult:
        result = WikidataImportResult()

        q_ids = await self._resolve_item_ids(req)
        if not q_ids:
            result.errors.append("No Wikidata items resolved from the provided class_ids / item_ids")
            return result

        items = await self._fetch_items(q_ids)

        # Upsert entities
        entity_map: dict[str, str] = {}  # q_id → entmoot entity_id
        for item in items:
            try:
                entity_id, created = await self._upsert_entity(item, req.domain_slugs)
                entity_map[item.q_id] = entity_id
                if created:
                    result.entities_created += 1
                else:
                    result.entities_skipped += 1
            except Exception as exc:
                result.errors.append(f"{item.q_id}: entity upsert failed: {exc}")

        if not req.property_ids:
            return result

        # Upsert attributes
        prop_labels = await self._fetch_property_labels(req.property_ids)
        attr_map: dict[str, str] = {}  # p_id → entmoot attribute_id
        for p_id, label in prop_labels.items():
            try:
                attr_id, created = await self._upsert_attribute(p_id, label)
                attr_map[p_id] = attr_id
                if created:
                    result.attributes_created += 1
                else:
                    result.attributes_skipped += 1
            except Exception as exc:
                result.errors.append(f"{p_id}: attribute upsert failed: {exc}")

        # Fetch and create values
        valid_q_ids = [q for q in q_ids if q in entity_map]
        if valid_q_ids and attr_map:
            statements = await self._fetch_statements(valid_q_ids, list(attr_map.keys()))
            for stmt in statements:
                entity_id = entity_map.get(stmt.q_id)
                attr_id = attr_map.get(stmt.p_id)
                if not entity_id or not attr_id:
                    continue
                try:
                    await self._create_value(
                        entity_id,
                        attr_id,
                        stmt.value,
                        f"{WIKIDATA_ITEM_BASE}{stmt.q_id}",
                    )
                    result.values_created += 1
                except Exception as exc:
                    result.errors.append(
                        f"{stmt.q_id}/{stmt.p_id}: value creation failed: {exc}"
                    )

        return result

    # ------------------------------------------------------------------
    # Resolve Q-IDs
    # ------------------------------------------------------------------

    async def _resolve_item_ids(self, req: WikidataImportRequest) -> list[str]:
        ids: set[str] = set(req.item_ids)
        for class_id in req.class_ids:
            query = f"""
SELECT DISTINCT ?item WHERE {{
  ?item wdt:P31 wd:{class_id} .
}} LIMIT 1000
"""
            rows = await self._sparql(query)
            for row in rows:
                uri = row.get("item", {}).get("value", "")
                if uri:
                    ids.add(_extract_id(uri))
        return list(ids)

    # ------------------------------------------------------------------
    # Fetch item labels and aliases
    # ------------------------------------------------------------------

    async def _fetch_items(self, q_ids: list[str]) -> list[_Item]:
        items: dict[str, _Item] = {}
        for batch in _batches(q_ids, BATCH_SIZE):
            values_clause = " ".join(f"wd:{q}" for q in batch)
            query = f"""
SELECT ?item ?itemLabel ?altLabel WHERE {{
  VALUES ?item {{ {values_clause} }}
  OPTIONAL {{ ?item skos:altLabel ?altLabel . FILTER(LANG(?altLabel) = "en") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
"""
            rows = await self._sparql(query)
            for row in rows:
                uri = row.get("item", {}).get("value", "")
                if not uri:
                    continue
                q_id = _extract_id(uri)
                label = row.get("itemLabel", {}).get("value", q_id)
                if q_id not in items:
                    items[q_id] = _Item(q_id=q_id, label=label)
                alias = row.get("altLabel", {}).get("value")
                if alias and alias not in items[q_id].aliases:
                    items[q_id].aliases.append(alias)

        return list(items.values())

    # ------------------------------------------------------------------
    # Fetch property labels
    # ------------------------------------------------------------------

    async def _fetch_property_labels(self, p_ids: list[str]) -> dict[str, str]:
        labels: dict[str, str] = {}
        for batch in _batches(p_ids, BATCH_SIZE):
            values_clause = " ".join(f"wd:{p}" for p in batch)
            query = f"""
SELECT ?prop ?propLabel WHERE {{
  VALUES ?prop {{ {values_clause} }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
"""
            rows = await self._sparql(query)
            for row in rows:
                uri = row.get("prop", {}).get("value", "")
                if not uri:
                    continue
                p_id = _extract_id(uri)
                label = row.get("propLabel", {}).get("value", p_id)
                labels[p_id] = label
        return labels

    # ------------------------------------------------------------------
    # Fetch statements
    # ------------------------------------------------------------------

    async def _fetch_statements(self, q_ids: list[str], p_ids: list[str]) -> list[_Statement]:
        stmts: list[_Statement] = []
        props_clause = " ".join(f"wdt:{p}" for p in p_ids)
        for batch in _batches(q_ids, BATCH_SIZE):
            items_clause = " ".join(f"wd:{q}" for q in batch)
            query = f"""
SELECT ?item ?prop ?value WHERE {{
  VALUES ?item {{ {items_clause} }}
  VALUES ?prop {{ {props_clause} }}
  ?item ?prop ?value .
  FILTER(
    DATATYPE(?value) = xsd:string ||
    DATATYPE(?value) = xsd:decimal ||
    DATATYPE(?value) = xsd:integer ||
    DATATYPE(?value) = xsd:dateTime
  )
}}
"""
            rows = await self._sparql(query)
            for row in rows:
                item_uri = row.get("item", {}).get("value", "")
                prop_uri = row.get("prop", {}).get("value", "")
                raw_value = row.get("value", {}).get("value", "")
                if not item_uri or not prop_uri or not raw_value:
                    continue
                # Defensive: skip item references that slipped through
                if raw_value.startswith(WIKIDATA_ENTITY_URI):
                    continue
                stmts.append(
                    _Statement(
                        q_id=_extract_id(item_uri),
                        p_id=_extract_id(prop_uri),
                        value=str(raw_value),
                    )
                )
        return stmts

    # ------------------------------------------------------------------
    # Graph writes
    # ------------------------------------------------------------------

    async def _upsert_entity(
        self, item: _Item, domain_slugs: list[str]
    ) -> tuple[str, bool]:
        existing = await self._graph.run(
            "MATCH (e:Entity {wikidata_id: $wid}) RETURN e.id AS id",
            {"wid": item.q_id},
        )
        if existing:
            return existing[0]["id"], False

        entity_id = str(uuid4())
        now = _now()
        await self._graph.run(
            """
            CREATE (:Entity {
              id: $id,
              name: $name,
              aliases: $aliases,
              wikidata_id: $wid,
              visibility: 'public',
              created_at: $now,
              updated_at: $now
            })
            """,
            {
                "id": entity_id,
                "name": item.label,
                "aliases": item.aliases,
                "wid": item.q_id,
                "now": now,
            },
        )
        for slug in domain_slugs:
            await self._graph.run(
                """
                MATCH (e:Entity {id: $entity_id})
                MATCH (d:Domain {slug: $slug})
                CREATE (e)-[:BELONGS_TO]->(d)
                """,
                {"entity_id": entity_id, "slug": slug},
            )
        return entity_id, True

    async def _upsert_attribute(self, p_id: str, label: str) -> tuple[str, bool]:
        existing = await self._graph.run(
            "MATCH (a:Attribute {wikidata_id: $wid}) RETURN a.id AS id",
            {"wid": p_id},
        )
        if existing:
            return existing[0]["id"], False

        attr_id = str(uuid4())
        now = _now()
        await self._graph.run(
            """
            CREATE (:Attribute {
              id: $id,
              name: $name,
              wikidata_id: $wid,
              visibility: 'public',
              created_at: $now
            })
            """,
            {"id": attr_id, "name": label, "wid": p_id, "now": now},
        )
        return attr_id, True

    async def _create_value(
        self, entity_id: str, attr_id: str, value: str, source_url: str
    ) -> None:
        value_id = str(uuid4())
        now = _now()
        await self._graph.run(
            """
            MATCH (e:Entity {id: $entity_id})
            MATCH (a:Attribute {id: $attr_id})
            CREATE (v:Value {
              id: $id,
              value: $value,
              source_type: 'scraped',
              confidence: 1.0,
              visibility: 'public',
              contributed_at: $now
            })
            CREATE (v)-[:DESCRIBES]->(e)
            CREATE (v)-[:FOR_ATTRIBUTE]->(a)
            """,
            {
                "id": value_id,
                "entity_id": entity_id,
                "attr_id": attr_id,
                "value": value,
                "now": now,
            },
        )
        source_id = str(uuid4())
        await self._graph.run(
            """
            MATCH (v:Value {id: $value_id})
            CREATE (s:Source {id: $source_id, href: $href, accessed_at: $now})
            CREATE (v)-[:SOURCED_FROM]->(s)
            """,
            {"value_id": value_id, "source_id": source_id, "href": source_url, "now": now},
        )

    # ------------------------------------------------------------------
    # SPARQL helper
    # ------------------------------------------------------------------

    async def _sparql(self, query: str) -> list[dict]:
        resp = await self._http.get(
            SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": USER_AGENT,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["results"]["bindings"]
