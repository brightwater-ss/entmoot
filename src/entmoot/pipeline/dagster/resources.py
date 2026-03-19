"""Dagster resources for Entmoot pipelines.

Resources are injected into Dagster assets at execution time.
They are configured from Entmoot's pydantic-settings config so a single
`.env` file controls both the Litestar API and the Dagster daemon.
"""

from __future__ import annotations

from dagster import ConfigurableResource
from falkordb.asyncio import FalkorDB

from entmoot.graph.driver import AsyncGraph


class FalkorDBResource(ConfigurableResource):
    """Provides an `AsyncGraph` connection to Dagster assets.

    Creates a fresh FalkorDB connection per asset execution — does NOT
    use the global `_db`/`_graph` state in `entmoot.graph.driver`,
    which is reserved for the Litestar application lifecycle.
    """

    host: str = "localhost"
    port: int = 6379
    graph_name: str = "entmoot"

    async def create_graph(self) -> AsyncGraph:
        db = FalkorDB(host=self.host, port=self.port)
        graph = db.select_graph(self.graph_name)
        return AsyncGraph(graph)
