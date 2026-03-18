import asyncio

import pytest
from litestar.testing import AsyncTestClient

from entmoot.app import create_app
from entmoot.config import settings
from entmoot.graph import close_driver, init_driver, init_schema


def falkordb_available() -> bool:
    """Return True if a FalkorDB server is reachable at the configured host/port."""
    try:
        from falkordb.asyncio import FalkorDB

        async def _check() -> bool:
            db = FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port)
            try:
                await db.list_graphs()
                return True
            except Exception:
                return False
            finally:
                await db.aclose()

        return asyncio.run(_check())
    except Exception:
        return False


requires_falkordb = pytest.mark.skipif(
    not falkordb_available(),
    reason="FalkorDB not available — start with: docker run -p 6379:6379 falkordb/falkordb",
)


@pytest.fixture(scope="session")
async def graph():
    try:
        g = await init_driver()
        await init_schema(g)
    except Exception as exc:
        pytest.skip(f"FalkorDB not available: {exc}")
    yield g
    await close_driver()


@pytest.fixture()
async def client(graph):
    test_app = create_app(connect_db=False)
    test_app.state.graph = graph
    async with AsyncTestClient(app=test_app) as c:
        yield c


@pytest.fixture()
def admin_headers():
    return {"x-admin-key": settings.admin_api_key}
