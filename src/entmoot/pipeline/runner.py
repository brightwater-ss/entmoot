"""Pipeline runner abstraction.

The `PipelineRunner` protocol is the sole interface that routes and tests
depend on. Two implementations are provided:

- `NullPipelineRunner`: runs pipeline handlers in-process (synchronous).
  Used by default; requires no extra dependencies. Ideal for development
  and testing. `trigger()` blocks until complete and returns status="success".

- `DagsterPipelineRunner` (optional): delegates to Dagster. Requires the
  `dagster` extra (`uv sync --extra dagster`). `trigger()` submits a job
  and returns status="pending"; poll `get_run()` for completion.

To add a new pipeline, register a `PipelineHandler` when constructing
`NullPipelineRunner`, and add a corresponding Dagster asset in
`entmoot.pipeline.dagster.assets`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel


class PipelineRun(BaseModel):
    """Unified run record returned by both NullPipelineRunner and DagsterPipelineRunner."""

    run_id: str
    pipeline_id: str
    status: Literal["pending", "running", "success", "failed", "cancelled"]
    triggered_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


# A handler is an async callable that receives pipeline params and returns a
# result dict. The NullPipelineRunner dispatches to these.
PipelineHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class PipelineRunner(Protocol):
    """Abstract interface for pipeline orchestration.

    Implementations must be injected at app startup via `app.state.pipeline_runner`.
    Routes and tests should never import a concrete implementation directly.
    """

    async def trigger(self, pipeline_id: str, params: dict[str, Any]) -> PipelineRun:
        """Trigger a pipeline run. Returns immediately (may be pending or complete)."""
        ...

    async def get_run(self, run_id: str) -> PipelineRun:
        """Return the current state of a run by ID."""
        ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class NullPipelineRunner:
    """In-process pipeline runner. Runs handlers synchronously.

    All runs complete before `trigger()` returns (status="success").
    Run history is stored in memory for the lifetime of the process.

    Usage::

        runner = NullPipelineRunner(handlers={
            "wikidata_import": make_wikidata_handler(graph),
        })
    """

    def __init__(self, handlers: dict[str, PipelineHandler]) -> None:
        self._handlers = handlers
        self._runs: dict[str, PipelineRun] = {}

    async def trigger(self, pipeline_id: str, params: dict[str, Any]) -> PipelineRun:
        handler = self._handlers.get(pipeline_id)
        if handler is None:
            raise KeyError(f"No handler registered for pipeline '{pipeline_id}'")

        run_id = str(uuid4())
        now = _now()
        run = PipelineRun(
            run_id=run_id,
            pipeline_id=pipeline_id,
            status="running",
            triggered_at=now,
            started_at=now,
        )
        self._runs[run_id] = run

        try:
            result = await handler(params)
            finished = _now()
            run = run.model_copy(update={
                "status": "success",
                "finished_at": finished,
                "result": result,
            })
        except Exception as exc:
            finished = _now()
            run = run.model_copy(update={
                "status": "failed",
                "finished_at": finished,
                "error": str(exc),
            })

        self._runs[run_id] = run
        return run

    async def get_run(self, run_id: str) -> PipelineRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"Run '{run_id}' not found")
        return run
