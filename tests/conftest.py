import pytest
from litestar.testing import AsyncTestClient

from entmoot.app import create_app
from entmoot.config import settings
from entmoot.graph import close_driver, init_driver, init_schema

# --- Neo4j availability ---

def neo4j_available() -> bool:
    """Return True if a Neo4j instance is reachable at the configured URI."""
    import asyncio

    from neo4j import AsyncGraphDatabase

    async def _check() -> bool:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        try:
            await driver.verify_connectivity()
            return True
        except Exception:
            return False
        finally:
            await driver.close()

    return asyncio.run(_check())


requires_neo4j = pytest.mark.skipif(
    not neo4j_available(),
    reason="Neo4j not available at configured URI",
)

# --- Fixtures ---

@pytest.fixture(scope="session")
async def neo4j_driver():
    """Session-scoped driver. Skips if Neo4j is not reachable."""
    try:
        driver = await init_driver()
        await init_schema(driver)
    except Exception as exc:
        pytest.skip(f"Neo4j not available: {exc}")
    yield driver
    await close_driver()


@pytest.fixture()
async def client(neo4j_driver):
    """AsyncTestClient backed by the test Neo4j driver (no startup hooks)."""
    test_app = create_app(connect_db=False)
    test_app.state.neo4j = neo4j_driver
    async with AsyncTestClient(app=test_app) as c:
        yield c


@pytest.fixture()
def admin_headers():
    return {"x-admin-key": settings.admin_api_key}
