from litestar import Controller, Request, get
from litestar.exceptions import NotFoundException

from entmoot.graph import AsyncGraph
from entmoot.models import EntitySummary, EntityWithFacts
from entmoot.models.value import SOURCE_TYPE_ORDER, ValueGroup, ValueResponse


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
            OPTIONAL MATCH (v:Value)-[:DESCRIBES]->(e)
            WHERE v.visibility = 'public'
            OPTIONAL MATCH (v)-[:FOR_ATTRIBUTE]->(a:Attribute)
            WHERE $attribute IS NULL OR a.id = $attribute
            OPTIONAL MATCH (v)-[:SOURCED_FROM]->(s:Source)
            RETURN e, domains, claimed_by, merged_into,
                   collect({
                     value_id: v.id,
                     value_value: v.value,
                     value_source_type: v.source_type,
                     value_confidence: v.confidence,
                     value_contributed_at: v.contributed_at,
                     value_org_id: v.org_id,
                     attribute_id: a.id,
                     attribute_name: a.name,
                     source_url: s.href
                   }) AS value_rows
            """,
            {"id": entity_id, "attribute": attribute},
        )

        if not records:
            raise NotFoundException(detail=f"Entity '{entity_id}' not found")

        row = records[0]
        entity = row["e"]

        # Group values by attribute, compute conflict per group
        groups: dict[str, dict] = {}
        for vr in row["value_rows"] or []:
            if not vr.get("value_id") or not vr.get("attribute_id"):
                continue
            attr_id = vr["attribute_id"]
            if attr_id not in groups:
                groups[attr_id] = {
                    "attribute_id": attr_id,
                    "attribute_name": vr["attribute_name"],
                    "values": [],
                }
            groups[attr_id]["values"].append(
                ValueResponse(
                    id=vr["value_id"],
                    value=vr["value_value"],
                    source_type=vr["value_source_type"],
                    source_url=vr.get("source_url"),
                    confidence=vr["value_confidence"],
                    org_id=vr.get("value_org_id"),
                    contributed_at=vr["value_contributed_at"],
                    conflict=False,
                )
            )

        value_groups: list[ValueGroup] = []
        for g in groups.values():
            distinct_values = {v.value for v in g["values"]}
            conflict = len(distinct_values) > 1
            for v in g["values"]:
                v.conflict = conflict
            g["values"].sort(
                key=lambda v: SOURCE_TYPE_ORDER.index(v.source_type)
                if v.source_type in SOURCE_TYPE_ORDER
                else 99
            )
            value_groups.append(
                ValueGroup(
                    attribute_id=g["attribute_id"],
                    attribute_name=g["attribute_name"],
                    values=g["values"],
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
            value_groups=value_groups,
        )
