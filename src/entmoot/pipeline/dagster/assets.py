"""Dagster asset definitions for Entmoot ingestion pipelines.

Each asset wraps a core pipeline class from `entmoot.pipeline.*`.
Core classes have no Dagster dependency — only this file does.

To add a new pipeline:
1. Implement the core logic in `entmoot/pipeline/<name>.py`
2. Register a `PipelineHandler` in `app.py` for the NullPipelineRunner
3. Add a Dagster `@asset` here wrapping the same core class
4. Register the asset in `definitions.py`
"""

from __future__ import annotations

import httpx
from dagster import AssetExecutionContext, Config, asset

from entmoot.models.admin import WikidataImportRequest
from entmoot.pipeline.wikidata import WikidataImporter

from .resources import FalkorDBResource


class WikidataImportConfig(Config):
    """Run-time configuration for the wikidata_import asset.

    Pass these values when materializing the asset from the Dagster UI
    or when triggering a job via the API.
    """

    class_ids: list[str] = []
    item_ids: list[str] = []
    property_ids: list[str] = []
    domain_slugs: list[str] = []


@asset(
    group_name="ingestion",
    name="wikidata_import",
    description="Import entities and values from Wikidata into the Entmoot knowledge graph.",
)
async def wikidata_import_asset(
    context: AssetExecutionContext,
    config: WikidataImportConfig,
    falkordb: FalkorDBResource,
) -> dict:
    """Materialise Wikidata entities and values into FalkorDB.

    Idempotent: existing entities/attributes (matched by wikidata_id) are
    skipped. Values are always appended (append-only per ADR-001).
    """
    graph = await falkordb.create_graph()
    req = WikidataImportRequest(
        class_ids=config.class_ids,
        item_ids=config.item_ids,
        property_ids=config.property_ids,
        domain_slugs=config.domain_slugs,
    )
    async with httpx.AsyncClient() as http:
        result = await WikidataImporter(graph=graph, http=http).run(req)

    context.log.info(
        f"wikidata_import complete: "
        f"entities_created={result.entities_created} "
        f"entities_skipped={result.entities_skipped} "
        f"attributes_created={result.attributes_created} "
        f"values_created={result.values_created} "
        f"errors={len(result.errors)}"
    )
    if result.errors:
        for err in result.errors:
            context.log.warning(f"non-fatal error: {err}")

    return result.model_dump()
