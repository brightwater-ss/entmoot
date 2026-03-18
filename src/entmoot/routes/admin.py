from datetime import datetime, timezone
from uuid import uuid4

from litestar import Controller, Request, post
from litestar.exceptions import NotFoundException
from neo4j import AsyncDriver

from entmoot.guards import admin_guard
from entmoot.models import (
    AttributeResponse,
    CreateAttributeRequest,
    CreateDomainRequest,
    CreateEntityRequest,
    CreateFactRequest,
    DomainResponse,
    EntityResponse,
    FactResponse,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdminController(Controller):
    path = "/admin"
    guards = [admin_guard]

    @post("/domains")
    async def create_domain(
        self,
        request: Request,
        data: CreateDomainRequest,
    ) -> DomainResponse:
        driver: AsyncDriver = request.app.state.neo4j
        domain_id = str(uuid4())
        now = _now()

        async with driver.session() as session:
            if data.parent_slug:
                result = await session.run(
                    """
                    MATCH (parent:Domain {slug: $parent_slug})
                    CREATE (d:Domain {id: $id, name: $name, slug: $slug, created_at: $now})
                    CREATE (parent)-[:PARENT_OF]->(d)
                    RETURN d
                    """,
                    {
                        "id": domain_id,
                        "name": data.name,
                        "slug": data.slug,
                        "now": now,
                        "parent_slug": data.parent_slug,
                    },
                )
            else:
                result = await session.run(
                    """
                    CREATE (d:Domain {id: $id, name: $name, slug: $slug, created_at: $now})
                    RETURN d
                    """,
                    {"id": domain_id, "name": data.name, "slug": data.slug, "now": now},
                )
            records = await result.data()

        d = records[0]["d"]
        return DomainResponse(id=d["id"], name=d["name"], slug=d["slug"])

    @post("/entities")
    async def create_entity(
        self,
        request: Request,
        data: CreateEntityRequest,
    ) -> EntityResponse:
        driver: AsyncDriver = request.app.state.neo4j
        entity_id = str(uuid4())
        now = _now()

        async with driver.session() as session:
            result = await session.run(
                """
                CREATE (e:Entity {
                  id: $id,
                  name: $name,
                  aliases: $aliases,
                  visibility: 'public',
                  created_at: $now,
                  updated_at: $now
                })
                WITH e
                UNWIND CASE WHEN $domain_slugs = [] THEN [null] ELSE $domain_slugs END AS slug
                OPTIONAL MATCH (d:Domain {slug: slug})
                FOREACH (_ IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
                  CREATE (e)-[:BELONGS_TO]->(d)
                )
                WITH e
                OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Domain)
                RETURN e, collect(d.name) AS domains
                """,
                {
                    "id": entity_id,
                    "name": data.name,
                    "aliases": data.aliases,
                    "domain_slugs": data.domain_slugs,
                    "now": now,
                },
            )
            records = await result.data()

        row = records[0]
        e = row["e"]
        return EntityResponse(
            id=e["id"],
            name=e["name"],
            aliases=e.get("aliases") or [],
            domains=row["domains"],
            claimed_by=None,
            merged_into=None,
            created_at=e["created_at"],
            updated_at=e["updated_at"],
        )

    @post("/attributes")
    async def create_attribute(
        self,
        request: Request,
        data: CreateAttributeRequest,
    ) -> AttributeResponse:
        driver: AsyncDriver = request.app.state.neo4j
        attribute_id = str(uuid4())
        now = _now()

        async with driver.session() as session:
            result = await session.run(
                """
                CREATE (a:Attribute {
                  id: $id,
                  name: $name,
                  description: $description,
                  unit: $unit,
                  visibility: 'public',
                  created_at: $now
                })
                WITH a
                UNWIND CASE WHEN $domain_slugs = [] THEN [null] ELSE $domain_slugs END AS slug
                OPTIONAL MATCH (d:Domain {slug: slug})
                FOREACH (_ IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
                  CREATE (a)-[:APPLICABLE_TO]->(d)
                )
                WITH a
                OPTIONAL MATCH (a)-[:APPLICABLE_TO]->(d:Domain)
                RETURN a, collect(d.name) AS domains
                """,
                {
                    "id": attribute_id,
                    "name": data.name,
                    "description": data.description,
                    "unit": data.unit,
                    "domain_slugs": data.domain_slugs,
                    "now": now,
                },
            )
            records = await result.data()

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

    @post("/facts")
    async def create_fact(
        self,
        request: Request,
        data: CreateFactRequest,
    ) -> FactResponse:
        driver: AsyncDriver = request.app.state.neo4j
        fact_id = str(uuid4())
        now = _now()

        async with driver.session() as session:
            # Verify entity and attribute exist
            check = await session.run(
                """
                OPTIONAL MATCH (e:Entity {id: $entity_id})
                OPTIONAL MATCH (a:Attribute {id: $attribute_id})
                RETURN e IS NOT NULL AS entity_exists, a IS NOT NULL AS attribute_exists
                """,
                {"entity_id": data.entity_id, "attribute_id": data.attribute_id},
            )
            check_row = (await check.data())[0]
            if not check_row["entity_exists"]:
                raise NotFoundException(detail=f"Entity '{data.entity_id}' not found")
            if not check_row["attribute_exists"]:
                raise NotFoundException(detail=f"Attribute '{data.attribute_id}' not found")

            # Create fact with source node if URL provided
            if data.source_url:
                result = await session.run(
                    """
                    MATCH (e:Entity {id: $entity_id})
                    MATCH (a:Attribute {id: $attribute_id})
                    CREATE (f:Fact {
                      id: $id,
                      value: $value,
                      source_type: $source_type,
                      confidence: $confidence,
                      visibility: 'public',
                      contributed_at: $now
                    })
                    CREATE (f)-[:DESCRIBES]->(e)
                    CREATE (f)-[:FOR_ATTRIBUTE]->(a)
                    CREATE (s:Source {id: $source_id, href: $source_url, accessed_at: $now})
                    CREATE (f)-[:SOURCED_FROM]->(s)
                    RETURN f
                    """,
                    {
                        "id": fact_id,
                        "entity_id": data.entity_id,
                        "attribute_id": data.attribute_id,
                        "value": data.value,
                        "source_type": data.source_type,
                        "confidence": data.confidence,
                        "source_url": data.source_url,
                        "source_id": str(uuid4()),
                        "now": now,
                    },
                )
            else:
                result = await session.run(
                    """
                    MATCH (e:Entity {id: $entity_id})
                    MATCH (a:Attribute {id: $attribute_id})
                    CREATE (f:Fact {
                      id: $id,
                      value: $value,
                      source_type: $source_type,
                      confidence: $confidence,
                      visibility: 'public',
                      contributed_at: $now
                    })
                    CREATE (f)-[:DESCRIBES]->(e)
                    CREATE (f)-[:FOR_ATTRIBUTE]->(a)
                    RETURN f
                    """,
                    {
                        "id": fact_id,
                        "entity_id": data.entity_id,
                        "attribute_id": data.attribute_id,
                        "value": data.value,
                        "source_type": data.source_type,
                        "confidence": data.confidence,
                        "now": now,
                    },
                )
            records = await result.data()

        f = records[0]["f"]
        return FactResponse(
            id=f["id"],
            value=f["value"],
            source_type=f["source_type"],
            source_url=data.source_url,
            confidence=f["confidence"],
            org_id=None,
            contributed_at=f["contributed_at"],
            conflict=False,
        )
