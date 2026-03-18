from typing import Any

from falkordb import Edge, Node
from falkordb.asyncio import FalkorDB

from entmoot.config import settings

_db: FalkorDB | None = None
_graph = None


async def init_driver():
    global _db, _graph
    _db = FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port)
    _graph = _db.select_graph(settings.falkordb_graph)
    return AsyncGraph(_graph)


async def get_graph() -> "AsyncGraph":
    if _graph is None:
        raise RuntimeError("Graph not initialized — call init_driver() first")
    return AsyncGraph(_graph)


async def close_driver() -> None:
    global _db, _graph
    if _db is not None:
        await _db.aclose()
    _db = None
    _graph = None


class AsyncGraph:
    """Thin wrapper around the native async FalkorDB graph handle."""

    def __init__(self, graph) -> None:
        self._g = graph

    async def run(self, cypher: str, params: dict | None = None) -> list[dict]:
        result = await self._g.query(cypher, params or {})
        return _normalize(result)

    async def schema(self, fn, *args) -> None:
        await fn(*args)


def _normalize(result) -> list[dict]:
    """Convert FalkorDB QueryResult to a list of dicts."""
    if not result.result_set:
        return []
    headers = [h[1] if isinstance(h, (list, tuple)) else h for h in result.header]
    return [
        {h: _to_python(v) for h, v in zip(headers, row)}
        for row in result.result_set
    ]


def _to_python(val: Any) -> Any:
    """Recursively convert FalkorDB types to plain Python."""
    if isinstance(val, Node):
        return dict(val.properties)
    if isinstance(val, Edge):
        return dict(val.properties)
    if isinstance(val, list):
        return [_to_python(v) for v in val]
    return val
