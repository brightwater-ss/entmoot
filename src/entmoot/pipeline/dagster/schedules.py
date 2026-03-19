"""Dagster schedule definitions.

Schedules are defined here but not auto-enabled. Activate them explicitly
in the Dagster UI (http://localhost:3000) or via `dagster schedule start`.

To configure which items get imported on a schedule, edit the `run_config`
below or override it at activation time in the UI.
"""

from dagster import RunConfig, ScheduleDefinition

from .assets import WikidataImportConfig
from .jobs import wikidata_import_job

# Nightly import — runs at 02:00 UTC.
# class_ids and item_ids left empty by default; configure per deployment.
nightly_wikidata_schedule = ScheduleDefinition(
    name="nightly_wikidata_import",
    cron_schedule="0 2 * * *",
    job=wikidata_import_job,
    run_config=RunConfig(
        ops={
            "wikidata_import": WikidataImportConfig(
                class_ids=[],
                item_ids=[],
                property_ids=[],
                domain_slugs=[],
            )
        }
    ),
    description="Nightly Wikidata import (02:00 UTC). Configure class_ids/item_ids before enabling.",
)
