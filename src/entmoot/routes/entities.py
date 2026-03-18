from litestar import Controller, Request, get
from litestar.exceptions import NotFoundException

from entmoot.graph import AsyncGraph
from entmoot.models import EntitySummary, EntityWithFacts
from entmoot.models.fact import SOURCE_TYPE_ORDER, FactGroup, FactResponse


class EntityController(Controller):
    path = "/entities"

    @get("/")
    async def search_entities(
        self,
        request: Request,
        q: str = "",
        domain: str | None = None,
        limit: int = 20,
    ) -> list[EntitySummary]:
        graph: AsyncGraph = request.app.state.graph
        if q:
            records = await graph.run(
                """
                CALL db.idx.fulltext.queryNodes('Entity', $q) YIELD node AS e
                WHERE e.visibility = 'public'
                OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Domain)
                WITH e, collect(d.name) AS domains
                WHERE $domain IS NULL OR $domain IN domains
                RETURN e, domains
                ORDER BY e.name
                LIMIT $limit
                """,
                {"q": q, "domain": domain, "limit": limit},
            )
        else:
            records = await graph.run(
                """
                MATCH (e:Entity)
                WHERE e.visibility = 'public'
                OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Domain)
                WITH e, collect(d.name) AS domains
                WHERE $domain IS NULL OR $domain IN domains
                RETURN e, domains
                ORDER BY e.name
                LIMIT $limit
                """,
                {"domain": domain, "limit": limit},
            )

        return [
            EntitySummary(
                id=r["e"]["id"],
                name=r["e"]["name"],
                aliases=r["e"].get("aliases") or [],
                domains=r["domains"] or [],
            )
            for r in records
        ]

    @get("/{entity_id:str}")
    async def get_entity(
        self,
        request: Request,
        entity_id: str,
        attribute: str | None = None,
    ) -> EntityWithFacts:
        graph: AsyncGraph = request.app.state.graph

        records = await graph.run(
            """
            MATCH (e:Entity {id: $id})
            WHERE e.visibility = 'public'
            OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Domain)
            OPTIONAL MATCH (e)-[:CLAIMED_BY]->(org:Organization)
            OPTIONAL MATCH (e)-[:MERGED_INTO]->(merged:Entity)
            WITH e,
                 collect(DISTINCT d.name) AS domains,
                 org.name AS claimed_by,
                 merged.id AS merged_into
            OPTIONAL MATCH (f:Fact)-[:DESCRIBES]->(e)
            WHERE f.visibility = 'public'
            OPTIONAL MATCH (f)-[:FOR_ATTRIBUTE]->(a:Attribute)
            WHERE $attribute IS NULL OR a.id = $attribute
            OPTIONAL MATCH (f)-[:SOURCED_FROM]->(s:Source)
            RETURN e, domains, claimed_by, merged_into,
                   collect({
                     fact_id: f.id,
                     fact_value: f.value,
                     fact_source_type: f.source_type,
                     fact_confidence: f.confidence,
                     fact_contributed_at: f.contributed_at,
                     fact_org_id: f.org_id,
                     attribute_id: a.id,
                     attribute_name: a.name,
                     source_url: s.href
                   }) AS fact_rows
            """,
            {"id": entity_id, "attribute": attribute},
        )

        if not records:
            raise NotFoundException(detail=f"Entity '{entity_id}' not found")

        row = records[0]
        entity = row["e"]

        # Group facts by attribute, compute conflict per group
        groups: dict[str, dict] = {}
        for fr in row["fact_rows"] or []:
            if not fr.get("fact_id") or not fr.get("attribute_id"):
                continue
            attr_id = fr["attribute_id"]
            if attr_id not in groups:
                groups[attr_id] = {
                    "attribute_id": attr_id,
                    "attribute_name": fr["attribute_name"],
                    "facts": [],
                }
            groups[attr_id]["facts"].append(
                FactResponse(
                    id=fr["fact_id"],
                    value=fr["fact_value"],
                    source_type=fr["fact_source_type"],
                    source_url=fr.get("source_url"),
                    confidence=fr["fact_confidence"],
                    org_id=fr.get("fact_org_id"),
                    contributed_at=fr["fact_contributed_at"],
                    conflict=False,
                )
            )

        fact_groups: list[FactGroup] = []
        for g in groups.values():
            values = {fact.value for fact in g["facts"]}
            conflict = len(values) > 1
            for fact in g["facts"]:
                fact.conflict = conflict
            g["facts"].sort(
                key=lambda f: SOURCE_TYPE_ORDER.index(f.source_type)
                if f.source_type in SOURCE_TYPE_ORDER
                else 99
            )
            fact_groups.append(
                FactGroup(
                    attribute_id=g["attribute_id"],
                    attribute_name=g["attribute_name"],
                    facts=g["facts"],
                    conflict=conflict,
                )
            )

        return EntityWithFacts(
            id=entity["id"],
            name=entity["name"],
            aliases=entity.get("aliases") or [],
            domains=row["domains"] or [],
            claimed_by=row.get("claimed_by"),
            merged_into=row.get("merged_into"),
            created_at=entity["created_at"],
            updated_at=entity["updated_at"],
            fact_groups=fact_groups,
        )
