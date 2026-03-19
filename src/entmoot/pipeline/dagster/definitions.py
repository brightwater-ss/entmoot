"""Dagster Definitions entry point.

`dagster dev` loads this module via `[tool.dagster] module_name` in pyproject.toml.

Usage::

    uv sync --extra dagster
    dagster dev          # opens http://localhost:3000
    dagster asset list   # lists all registered assets
"""

from dagster import Definitions

from entmoot.config import settings

from .assets import wikidata_import_asset
from .jobs import wikidata_import_job
from .resources import FalkorDBResource
from .schedules import nightly_wikidata_schedule

defs = Definitions(
    assets=[wikidata_import_asset],
    jobs=[wikidata_import_job],
    schedules=[nightly_wikidata_schedule],
    resources={
        "falkordb": FalkorDBResource(
            host=settings.falkordb_host,
            port=settings.falkordb_port,
            graph_name=settings.falkordb_graph,
        )
    },
)
