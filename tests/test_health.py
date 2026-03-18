import pytest
from litestar.testing import AsyncTestClient

from entmoot.app import create_app


@pytest.mark.asyncio
async def test_health_returns_ok():
    """Health endpoint requires no database — always runs."""
    async with AsyncTestClient(app=create_app(connect_db=False)) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
