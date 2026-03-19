"""Dagster job definitions.

Jobs group assets into executable units. Schedules and the DagsterPipelineRunner
reference jobs by name.
"""

from dagster import define_asset_job

# Runs the wikidata_import asset. Config is passed at trigger time.
wikidata_import_job = define_asset_job(
    name="wikidata_import_job",
    selection=["wikidata_import"],
    description="Run the Wikidata import pipeline for a given set of Q-IDs / classes.",
)
