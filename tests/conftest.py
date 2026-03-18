import socket

import pytest
from litestar.testing import AsyncTestClient

from entmoot.app import create_app
from entmoot.config import settings
from entmoot.graph import close_driver, init_driver, init_schema


def falkordb_available() -> bool:
    """Return True if a FalkorDB server is reachable at the configured host/port."""
    try:
        with socket.create_connection(
            (settings.falkordb_host, settings.falkordb_port), timeout=1
        ):
            return True
    except OSError:
        return False


requires_falkordb = pytest.mark.skipif(
    not falkordb_available(),
    reason="FalkorDB not available — start with: docker run -p 6379:6379 falkordb/falkordb",
)


@pytest.fixture(scope="session")
async def graph():
    """Direct graph handle for schema-level tests (no HTTP layer)."""
    try:
        g = await init_driver()
        await init_schema(g)
    except Exception as exc:
        pytest.skip(f"FalkorDB not available: {exc}")
    yield g
    await close_driver()


@pytest.fixture()
async def client():
    """HTTP test client — app manages its own FalkorDB connection so the
    connection is created in the same event loop that handles requests."""
    if not falkordb_available():
        pytest.skip("FalkorDB not available — start with: docker run -p 6379:6379 falkordb/falkordb")
    test_app = create_app(connect_db=True)
    async with AsyncTestClient(app=test_app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def admin_headers():
    return {"x-admin-key": settings.admin_api_key}
