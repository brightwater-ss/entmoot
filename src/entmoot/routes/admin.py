from datetime import datetime, timezone
from uuid import uuid4

from litestar import Controller, Request, post
from litestar.exceptions import NotFoundException

from entmoot.graph import AsyncGraph
from entmoot.guards import admin_guard
from entmoot.models import (
    AttributeResponse,
    CreateAttributeRequest,
    CreateDomainRequest,
    CreateEntityRequest,
    CreateValueRequest,
    DomainResponse,
    EntityResponse,
    ValueResponse,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdminController(Controller):
    path = "/admin"
    guards = [admin_guard]

    @post("/domains")
    async def create_domain(self, request: Request, data: CreateDomainRequest) -> DomainResponse:
        graph: AsyncGraph = request.app.state.graph
        domain_id = str(uuid4())
        now = _now()

        await graph.run(
            "CREATE (:Domain {id: $id, name: $name, slug: $slug, created_at: $now})",
            {"id": domain_id, "name": data.name, "slug": data.slug, "now": now},
        )

        if data.parent_slug:
            await graph.run(
                """
                MATCH (parent:Domain {slug: $parent_slug})
                MATCH (d:Domain {id: $id})
                CREATE (parent)-[:PARENT_OF]->(d)
                """,
                {"parent_slug": data.parent_slug, "id": domain_id},
            )

        return DomainResponse(id=domain_id, name=data.name, slug=data.slug)

    @post("/entities")
    async def create_entity(self, request: Request, data: CreateEntityRequest) -> EntityResponse:
        graph: AsyncGraph = request.app.state.graph
        entity_id = str(uuid4())
        now = _now()

        await graph.run(
            """
            CREATE (:Entity {
              id: $id,
              name: $name,
              aliases: $aliases,
              visibility: 'public',
              created_at: $now,
              updated_at: $now
            })
            """,
            {"id": entity_id, "name": data.name, "aliases": data.aliases, "now": now},
        )

        for slug in data.domain_slugs:
            await graph.run(
                """
                MATCH (e:Entity {id: $entity_id})
                MATCH (d:Domain {slug: $slug})
                CREATE (e)-[:BELONGS_TO]->(d)
                """,
                {"entity_id": entity_id, "slug": slug},
            )

        domain_records = await graph.run(
            "MATCH (e:Entity {id: $id})-[:BELONGS_TO]->(d:Domain) RETURN d.name AS name",
            {"id": entity_id},
        )
        domains = [r["name"] for r in domain_records]

        return EntityResponse(
            id=entity_id,
            name=data.name,
            aliases=data.aliases,
            domains=domains,
            claimed_by=None,
            merged_into=None,
            created_at=now,
            updated_at=now,
        )

    @post("/attributes")
    async def create_attribute(
        self, request: Request, data: CreateAttributeRequest
    ) -> AttributeResponse:
        graph: AsyncGraph = request.app.state.graph
        attribute_id = str(uuid4())
        now = _now()

        await graph.run(
            """
            CREATE (:Attribute {
              id: $id,
              name: $name,
              description: $description,
              unit: $unit,
              visibility: 'public',
              created_at: $now
            })
            """,
            {
                "id": attribute_id,
                "name": data.name,
                "description": data.description,
                "unit": data.unit,
                "now": now,
            },
        )

        for slug in data.domain_slugs:
            await graph.run(
                """
                MATCH (a:Attribute {id: $attribute_id})
                MATCH (d:Domain {slug: $slug})
                CREATE (a)-[:APPLICABLE_TO]->(d)
                """,
                {"attribute_id": attribute_id, "slug": slug},
            )

        domain_records = await graph.run(
            "MATCH (a:Attribute {id: $id})-[:APPLICABLE_TO]->(d:Domain) RETURN d.name AS name",
            {"id": attribute_id},
        )
        domains = [r["name"] for r in domain_records]

        return AttributeResponse(
            id=attribute_id,
            name=data.name,
            description=data.description,
            unit=data.unit,
            domains=domains,
            created_at=now,
        )

    @post("/values")
    async def create_value(self, request: Request, data: CreateValueRequest) -> ValueResponse:
        graph: AsyncGraph = request.app.state.graph

        entity_check = await graph.run(
            "MATCH (e:Entity {id: $id}) RETURN e.id AS id", {"id": data.entity_id}
        )
        if not entity_check:
            raise NotFoundException(detail=f"Entity '{data.entity_id}' not found")

        attr_check = await graph.run(
            "MATCH (a:Attribute {id: $id}) RETURN a.id AS id", {"id": data.attribute_id}
        )
        if not attr_check:
            raise NotFoundException(detail=f"Attribute '{data.attribute_id}' not found")

        value_id = str(uuid4())
        now = _now()

        await graph.run(
            """
            MATCH (e:Entity {id: $entity_id})
            MATCH (a:Attribute {id: $attribute_id})
            CREATE (v:Value {
              id: $id,
              value: $value,
              source_type: $source_type,
              confidence: $confidence,
              visibility: 'public',
              contributed_at: $now
            })
            CREATE (v)-[:DESCRIBES]->(e)
            CREATE (v)-[:FOR_ATTRIBUTE]->(a)
            """,
            {
                "id": value_id,
                "entity_id": data.entity_id,
                "attribute_id": data.attribute_id,
                "value": data.value,
                "source_type": data.source_type,
                "confidence": data.confidence,
                "now": now,
            },
        )

        if data.source_url:
            await graph.run(
                """
                MATCH (v:Value {id: $value_id})
                CREATE (s:Source {id: $source_id, href: $href, accessed_at: $now})
                CREATE (v)-[:SOURCED_FROM]->(s)
                """,
                {
                    "value_id": value_id,
                    "source_id": str(uuid4()),
                    "href": data.source_url,
                    "now": now,
                },
            )

        return ValueResponse(
            id=value_id,
            value=data.value,
            source_type=data.source_type,
            source_url=data.source_url,
            confidence=data.confidence,
            org_id=None,
            contributed_at=now,
            conflict=False,
        )
