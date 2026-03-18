from litestar import Controller, Request, get
from litestar.exceptions import NotFoundException
from neo4j import AsyncDriver

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
        driver: AsyncDriver = request.app.state.neo4j
        async with driver.session() as session:
            if q:
                result = await session.run(
                    """
                    CALL db.index.fulltext.queryNodes('entitySearch', $q)
                    YIELD node AS e, score
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
                result = await session.run(
                    """
                    MATCH (e:Entity)
                    WHERE e.visibility = 'public'
                      AND ($domain IS NULL OR EXISTS {
                        MATCH (e)-[:BELONGS_TO]->(d:Domain) WHERE d.name = $domain
                      })
                    OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Domain)
                    WITH e, collect(d.name) AS domains
                    RETURN e, domains
                    ORDER BY e.name
                    LIMIT $limit
                    """,
                    {"domain": domain, "limit": limit},
                )
            records = await result.data()

        return [
            EntitySummary(
                id=r["e"]["id"],
                name=r["e"]["name"],
                aliases=r["e"].get("aliases") or [],
                domains=r["domains"],
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
        driver: AsyncDriver = request.app.state.neo4j
        async with driver.session() as session:
            result = await session.run(
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
                  AND ($attribute IS NULL OR EXISTS {
                    MATCH (f)-[:FOR_ATTRIBUTE]->(a:Attribute) WHERE a.id = $attribute
                  })
                OPTIONAL MATCH (f)-[:FOR_ATTRIBUTE]->(a:Attribute)
                OPTIONAL MATCH (f)-[:SUBMITTED_BY]->(forg:Organization)
                OPTIONAL MATCH (f)-[:SOURCED_FROM]->(s:Source)
                RETURN e, domains, claimed_by, merged_into,
                       collect({
                         fact: f,
                         attribute_id: a.id,
                         attribute_name: a.name,
                         source_url: s.href
                       }) AS fact_rows
                """,
                {"id": entity_id, "attribute": attribute},
            )
            records = await result.data()

        if not records:
            raise NotFoundException(detail=f"Entity '{entity_id}' not found")

        row = records[0]
        entity = row["e"]

        # Group facts by attribute, compute conflict per group
        groups: dict[str, dict] = {}
        for fr in row["fact_rows"]:
            f = fr.get("fact")
            if not f or not fr.get("attribute_id"):
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
                    id=f["id"],
                    value=f["value"],
                    source_type=f["source_type"],
                    source_url=fr.get("source_url"),
                    confidence=f["confidence"],
                    org_id=f.get("org_id"),
                    contributed_at=f["contributed_at"],
                    conflict=False,  # set below after grouping
                )
            )

        fact_groups: list[FactGroup] = []
        for g in groups.values():
            values = {fact.value for fact in g["facts"]}
            conflict = len(values) > 1
            for fact in g["facts"]:
                fact.conflict = conflict
            # Sort by trust tier
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
            domains=row["domains"],
            claimed_by=row.get("claimed_by"),
            merged_into=row.get("merged_into"),
            created_at=entity["created_at"],
            updated_at=entity["updated_at"],
            fact_groups=fact_groups,
        )
