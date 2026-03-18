import asyncio

from entmoot.graph.driver import AsyncGraph

_UNIQUE_CONSTRAINTS = [
    ("Entity", "id"),
    ("Attribute", "id"),
    ("Domain", "id"),
    ("Domain", "slug"),
    ("Value", "id"),
    ("Organization", "id"),
    ("Organization", "slug"),
    ("Source", "id"),
]

_FULLTEXT_INDEXES = [
    ("Entity", ("name", "aliases")),
    ("Attribute", ("name",)),
]


async def init_schema(graph: AsyncGraph) -> None:
    """Create indexes and constraints, then wait until all are OPERATIONAL."""
    for label, prop in _UNIQUE_CONSTRAINTS:
        try:
            await graph._g.create_node_unique_constraint(label, prop)
        except Exception:
            pass  # already exists

    for label, props in _FULLTEXT_INDEXES:
        try:
            await graph._g.create_node_fulltext_index(label, *props)
        except Exception:
            pass  # already exists

    await _wait_for_constraints(graph)


async def _wait_for_constraints(graph: AsyncGraph, timeout: float = 10.0) -> None:
    """Poll until all unique constraints are OPERATIONAL (FalkorDB applies them async)."""
    expected = {(label, prop) for label, prop in _UNIQUE_CONSTRAINTS}
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        constraints = await graph._g.list_constraints()
        operational = {
            (c["label"], c["properties"][0])
            for c in constraints
            if c["status"] == "OPERATIONAL" and c["type"] == "UNIQUE"
        }
        if expected.issubset(operational):
            return
        await asyncio.sleep(0.1)
    raise TimeoutError("Timed out waiting for FalkorDB constraints to become OPERATIONAL")
