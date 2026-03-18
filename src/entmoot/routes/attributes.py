from litestar import Controller, Request, get
from litestar.exceptions import NotFoundException

from entmoot.graph import AsyncGraph
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
        graph: AsyncGraph = request.app.state.graph
        if q:
            records = await graph.run(
                """
                CALL db.idx.fulltext.queryNodes('Attribute', $q) YIELD node AS a
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
            records = await graph.run(
                """
                MATCH (a:Attribute)
                WHERE a.visibility = 'public'
                OPTIONAL MATCH (a)-[:APPLICABLE_TO]->(d:Domain)
                WITH a, collect(d.name) AS domains
                WHERE $domain IS NULL OR $domain IN domains
                RETURN a, domains
                ORDER BY a.name
                LIMIT $limit
                """,
                {"domain": domain, "limit": limit},
            )

        return [
            AttributeSummary(
                id=r["a"]["id"],
                name=r["a"]["name"],
                domain=r["domains"][0] if r["domains"] else None,
            )
            for r in records
        ]

    @get("/{attribute_id:str}")
    async def get_attribute(self, request: Request, attribute_id: str) -> AttributeResponse:
        graph: AsyncGraph = request.app.state.graph
        records = await graph.run(
            """
            MATCH (a:Attribute {id: $id})
            WHERE a.visibility = 'public'
            OPTIONAL MATCH (a)-[:APPLICABLE_TO]->(d:Domain)
            RETURN a, collect(d.name) AS domains
            """,
            {"id": attribute_id},
        )

        if not records:
            raise NotFoundException(detail=f"Attribute '{attribute_id}' not found")

        row = records[0]
        a = row["a"]
        return AttributeResponse(
            id=a["id"],
            name=a["name"],
            description=a.get("description"),
            unit=a.get("unit"),
            domains=row["domains"] or [],
            created_at=a["created_at"],
        )
