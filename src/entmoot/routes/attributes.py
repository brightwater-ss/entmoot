from litestar import Controller, Request, get
from neo4j import AsyncDriver

from entmoot.models import AttributeResponse, AttributeSummary


class AttributeController(Controller):
    path = "/attributes"

    @get("/")
    async def search_attributes(
        self,
        request: Request,
        q: str = "",
        domain: str | None = None,
        limit: int = 20,
    ) -> list[AttributeSummary]:
        driver: AsyncDriver = request.app.state.neo4j
        async with driver.session() as session:
            if q:
                result = await session.run(
                    """
                    CALL db.index.fulltext.queryNodes('attributeSearch', $q)
                    YIELD node AS a, score
                    WHERE a.visibility = 'public'
                    OPTIONAL MATCH (a)-[:APPLICABLE_TO]->(d:Domain)
                    WITH a, collect(d.name) AS domains
                    WHERE $domain IS NULL OR $domain IN domains
                    RETURN a, domains
                    ORDER BY a.name
                    LIMIT $limit
                    """,
                    {"q": q, "domain": domain, "limit": limit},
                )
            else:
                result = await session.run(
                    """
                    MATCH (a:Attribute)
                    WHERE a.visibility = 'public'
                      AND ($domain IS NULL OR EXISTS {
                        MATCH (a)-[:APPLICABLE_TO]->(d:Domain) WHERE d.name = $domain
                      })
                    OPTIONAL MATCH (a)-[:APPLICABLE_TO]->(d:Domain)
                    WITH a, collect(d.name) AS domains
                    RETURN a, domains
                    ORDER BY a.name
                    LIMIT $limit
                    """,
                    {"domain": domain, "limit": limit},
                )
            records = await result.data()

        return [
            AttributeSummary(
                id=r["a"]["id"],
                name=r["a"]["name"],
                domain=r["domains"][0] if r["domains"] else None,
            )
            for r in records
        ]

    @get("/{attribute_id:str}")
    async def get_attribute(
        self,
        request: Request,
        attribute_id: str,
    ) -> AttributeResponse:
        from litestar.exceptions import NotFoundException

        driver: AsyncDriver = request.app.state.neo4j
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Attribute {id: $id})
                WHERE a.visibility = 'public'
                OPTIONAL MATCH (a)-[:APPLICABLE_TO]->(d:Domain)
                RETURN a, collect(d.name) AS domains
                """,
                {"id": attribute_id},
            )
            records = await result.data()

        if not records:
            raise NotFoundException(detail=f"Attribute '{attribute_id}' not found")

        row = records[0]
        a = row["a"]
        return AttributeResponse(
            id=a["id"],
            name=a["name"],
            description=a.get("description"),
            unit=a.get("unit"),
            domains=row["domains"],
            created_at=a["created_at"],
        )
