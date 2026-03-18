import pytest

from entmoot.graph import init_schema
from tests.conftest import requires_falkordb


@requires_falkordb
@pytest.mark.asyncio
async def test_schema_init_is_idempotent(graph):
    """Running schema init twice must not raise."""
    await init_schema(graph)
