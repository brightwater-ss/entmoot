from entmoot.graph.driver import AsyncGraph


async def init_schema(graph: AsyncGraph) -> None:
    """Create indexes and constraints. All operations are idempotent."""

    for label, prop in [
        ("Entity", "id"),
        ("Attribute", "id"),
        ("Domain", "id"),
        ("Domain", "slug"),
        ("Fact", "id"),
        ("Organization", "id"),
        ("Organization", "slug"),
        ("Source", "id"),
    ]:
        try:
            await graph._g.create_node_unique_constraint(label, prop)
        except Exception:
            pass  # already exists

    for label, props in [
        ("Entity", ("name", "aliases")),
        ("Attribute", ("name",)),
    ]:
        try:
            await graph._g.create_node_fulltext_index(label, *props)
        except Exception:
            pass  # already exists
