from neo4j import AsyncDriver

# Constraints and full-text indexes per ADR-001
_SCHEMA_STATEMENTS = [
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT attribute_id IF NOT EXISTS FOR (n:Attribute) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT domain_id IF NOT EXISTS FOR (n:Domain) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT domain_slug IF NOT EXISTS FOR (n:Domain) REQUIRE n.slug IS UNIQUE",
    "CREATE CONSTRAINT fact_id IF NOT EXISTS FOR (n:Fact) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT org_id IF NOT EXISTS FOR (n:Organization) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT org_slug IF NOT EXISTS FOR (n:Organization) REQUIRE n.slug IS UNIQUE",
    "CREATE CONSTRAINT source_id IF NOT EXISTS FOR (n:Source) REQUIRE n.id IS UNIQUE",
    (
        "CREATE FULLTEXT INDEX entitySearch IF NOT EXISTS "
        "FOR (n:Entity) ON EACH [n.name, n.aliases]"
    ),
    (
        "CREATE FULLTEXT INDEX attributeSearch IF NOT EXISTS "
        "FOR (n:Attribute) ON EACH [n.name]"
    ),
]


async def init_schema(driver: AsyncDriver) -> None:
    async with driver.session() as session:
        for statement in _SCHEMA_STATEMENTS:
            await session.run(statement)
