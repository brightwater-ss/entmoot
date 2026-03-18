import pytest

from tests.conftest import requires_neo4j


@requires_neo4j
@pytest.mark.asyncio
async def test_schema_init_is_idempotent(neo4j_driver):
    """Running schema init twice must not raise — all statements use IF NOT EXISTS."""
    from entmoot.graph import init_schema
    await init_schema(neo4j_driver)  # second run
