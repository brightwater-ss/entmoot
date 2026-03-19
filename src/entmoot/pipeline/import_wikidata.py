"""Standalone Wikidata import script.

Usage:
    uv run python -m entmoot.pipeline.import_wikidata --help

Examples:
    # Dry run — resolve IDs and fetch labels without writing to graph
    uv run python -m entmoot.pipeline.import_wikidata \\
        --class Q4830453 --domains cloud-providers --dry-run

    # Import 3 companies with 2 properties
    uv run python -m entmoot.pipeline.import_wikidata \\
        --items Q95 Q37156 Q1552700 \\
        --props P571 P159 \\
        --domains cloud-providers
"""

import argparse
import asyncio
import sys

import httpx

from entmoot.graph import close_driver, init_driver, init_schema
from entmoot.models.admin import WikidataImportRequest
from entmoot.pipeline.wikidata import WikidataImporter


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m entmoot.pipeline.import_wikidata",
        description="Import entities and values from Wikidata into Entmoot.",
    )
    p.add_argument(
        "--class",
        dest="class_ids",
        nargs="+",
        metavar="QID",
        default=[],
        help="Wikidata class Q-IDs to import instances of (e.g. Q4830453 Q5)",
    )
    p.add_argument(
        "--items",
        dest="item_ids",
        nargs="+",
        metavar="QID",
        default=[],
        help="Explicit Wikidata item Q-IDs to import (e.g. Q95 Q37156)",
    )
    p.add_argument(
        "--props",
        dest="property_ids",
        nargs="+",
        metavar="PID",
        default=[],
        help="Wikidata property P-IDs to import as values (e.g. P571 P159)",
    )
    p.add_argument(
        "--domains",
        dest="domain_slugs",
        nargs="+",
        metavar="SLUG",
        default=[],
        help="Entmoot domain slugs to link imported entities to",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve IDs and fetch labels without writing to graph",
    )
    return p.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        req = WikidataImportRequest(
            class_ids=args.class_ids,
            item_ids=args.item_ids,
            property_ids=args.property_ids,
            domain_slugs=args.domain_slugs,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    graph = await init_driver()
    await init_schema(graph)

    try:
        async with httpx.AsyncClient() as http:
            importer = WikidataImporter(graph=graph, http=http)

            if args.dry_run:
                q_ids = await importer._resolve_item_ids(req)
                items = await importer._fetch_items(q_ids)
                print(f"Would import {len(items)} entities:")
                for item in items[:10]:
                    print(f"  {item.q_id}: {item.label}")
                if len(items) > 10:
                    print(f"  … and {len(items) - 10} more")
            else:
                result = await importer.run(req)
                print(f"entities_created:    {result.entities_created}")
                print(f"entities_skipped:    {result.entities_skipped}")
                print(f"attributes_created:  {result.attributes_created}")
                print(f"attributes_skipped:  {result.attributes_skipped}")
                print(f"values_created:      {result.values_created}")
                if result.errors:
                    print(f"errors ({len(result.errors)}):")
                    for err in result.errors:
                        print(f"  {err}")
    finally:
        await close_driver()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
