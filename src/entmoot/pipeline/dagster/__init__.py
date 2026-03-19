"""Dagster adapter for the Entmoot pipeline runner.

Requires the `dagster` optional dependency::

    uv sync --extra dagster

`DagsterPipelineRunner` implements the `PipelineRunner` protocol by submitting
Dagster jobs via `execute_in_process`. Because Dagster's execution API is
synchronous, it is dispatched to a thread pool so it does not block the
Litestar async event loop.

Future upgrade path: replace `execute_in_process` with a call to the Dagster
GraphQL API (requires `dagster-webserver` running) for true fire-and-forget
async execution. The `PipelineRunner` protocol does not need to change.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import partial
from typing import Any
from uuid import uuid4

from dagster import DagsterInstance, ReconstructableJob

from entmoot.pipeline.runner import PipelineRun

from .definitions import defs


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_job_sync(pipeline_id: str, params: dict[str, Any]) -> tuple[str, dict | None, str | None]:
    """Execute a Dagster job synchronously (called from a thread pool)."""
    job_name = f"{pipeline_id}_job"
    job_def = defs.get_job_def(job_name)

    # Map flat params dict to Dagster run_config ops structure
    run_config = {"ops": {pipeline_id: {"config": params}}}

    result = job_def.execute_in_process(
        run_config=run_config,
        instance=DagsterInstance.ephemeral(),
    )

    if result.success:
        output = result.output_for_node(pipeline_id)
        return result.run_id, output, None
    else:
        return result.run_id, None, "Dagster job failed — check Dagster logs for details"


class DagsterPipelineRunner:
    """PipelineRunner implementation backed by Dagster.

    `trigger()` submits the job to a thread pool and waits for completion,
    returning a completed `PipelineRun`. To make it truly non-blocking
    (return immediately with status="pending"), replace the `run_in_executor`
    call with a Dagster GraphQL submission and store the run in a persistent
    store accessible to `get_run()`.
    """

    def __init__(self) -> None:
        # In-memory run cache (process-lifetime). For multi-process or
        # persistent storage, swap this dict for a database-backed store.
        self._runs: dict[str, PipelineRun] = {}

    async def trigger(self, pipeline_id: str, params: dict[str, Any]) -> PipelineRun:
        run_id = str(uuid4())
        now = _now()

        # Run the synchronous Dagster job in a thread pool to avoid blocking
        # the async event loop
        loop = asyncio.get_event_loop()
        try:
            dagster_run_id, result_data, error = await loop.run_in_executor(
                None, partial(_run_job_sync, pipeline_id, params)
            )
        except Exception as exc:
            finished = _now()
            run = PipelineRun(
                run_id=run_id,
                pipeline_id=pipeline_id,
                status="failed",
                triggered_at=now,
                started_at=now,
                finished_at=finished,
                error=str(exc),
            )
            self._runs[run_id] = run
            return run

        finished = _now()
        run = PipelineRun(
            run_id=dagster_run_id,  # use Dagster's run ID for traceability
            pipeline_id=pipeline_id,
            status="success" if result_data is not None else "failed",
            triggered_at=now,
            started_at=now,
            finished_at=finished,
            result=result_data,
            error=error,
        )
        self._runs[run.run_id] = run
        return run

    async def get_run(self, run_id: str) -> PipelineRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"Run '{run_id}' not found")
        return run
