from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from litestar import Litestar, get
from litestar.datastructures import State

from entmoot.config import settings
from entmoot.graph import close_driver, init_driver, init_schema
from entmoot.models.admin import WikidataImportRequest
from entmoot.pipeline.runner import NullPipelineRunner, PipelineRunner
from entmoot.pipeline.wikidata import WikidataImporter
from entmoot.routes import AdminController, AttributeController, EntityController

if TYPE_CHECKING:
    from entmoot.graph.driver import AsyncGraph


@get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _make_wikidata_handler(graph: AsyncGraph):
    """Create a PipelineHandler closure for the wikidata_import pipeline."""

    async def handler(params: dict) -> dict:
        req = WikidataImportRequest(**params)
        async with httpx.AsyncClient() as http:
            importer = WikidataImporter(graph=graph, http=http)
            result = await importer.run(req)
        return result.model_dump()

    return handler


def _build_runner(graph: AsyncGraph) -> PipelineRunner:
    """Instantiate the configured PipelineRunner.

    Defaults to NullPipelineRunner (in-process). Set PIPELINE_RUNNER=dagster
    and install the dagster extra to use the Dagster orchestrator.
    """
    if settings.pipeline_runner == "dagster":
        # Deferred import — requires `uv sync --extra dagster`
        from entmoot.pipeline.dagster import DagsterPipelineRunner  # type: ignore[import]

        return DagsterPipelineRunner()

    return NullPipelineRunner(
        handlers={
            "wikidata_import": _make_wikidata_handler(graph),
        }
    )


def create_app(connect_db: bool = True) -> Litestar:
    async def on_startup(app: Litestar) -> None:
        graph = await init_driver()
        await init_schema(graph)
        app.state.graph = graph
        app.state.pipeline_runner = _build_runner(graph)

    async def on_shutdown(app: Litestar) -> None:
        await close_driver()

    return Litestar(
        route_handlers=[health, EntityController, AttributeController, AdminController],
        on_startup=[on_startup] if connect_db else [],
        on_shutdown=[on_shutdown] if connect_db else [],
        state=State({}),
    )


app = create_app()
