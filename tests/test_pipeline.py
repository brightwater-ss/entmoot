"""Tests for the PipelineRunner adapter abstraction.

These tests exercise NullPipelineRunner without requiring FalkorDB —
they validate the protocol contract that any future runner implementation
must satisfy.
"""

import pytest

from entmoot.pipeline.runner import NullPipelineRunner, PipelineRun


async def _ok_handler(params: dict) -> dict:
    return {"echo": params.get("msg", "ok")}


async def _fail_handler(params: dict) -> dict:
    raise RuntimeError("simulated failure")


@pytest.fixture()
def runner():
    return NullPipelineRunner(
        handlers={
            "ok_pipeline": _ok_handler,
            "fail_pipeline": _fail_handler,
        }
    )


@pytest.mark.asyncio
async def test_trigger_success(runner):
    run = await runner.trigger("ok_pipeline", {"msg": "hello"})
    assert isinstance(run, PipelineRun)
    assert run.status == "success"
    assert run.result == {"echo": "hello"}
    assert run.error is None
    assert run.finished_at is not None


@pytest.mark.asyncio
async def test_trigger_failure(runner):
    run = await runner.trigger("fail_pipeline", {})
    assert run.status == "failed"
    assert "simulated failure" in (run.error or "")
    assert run.result is None


@pytest.mark.asyncio
async def test_get_run_returns_stored_run(runner):
    run = await runner.trigger("ok_pipeline", {})
    fetched = await runner.get_run(run.run_id)
    assert fetched.run_id == run.run_id
    assert fetched.status == "success"


@pytest.mark.asyncio
async def test_get_run_unknown_id(runner):
    with pytest.raises(KeyError):
        await runner.get_run("nonexistent-id")


@pytest.mark.asyncio
async def test_trigger_unknown_pipeline(runner):
    with pytest.raises(KeyError):
        await runner.trigger("not_registered", {})


@pytest.mark.asyncio
async def test_pipeline_run_fields(runner):
    run = await runner.trigger("ok_pipeline", {"msg": "fields"})
    assert run.pipeline_id == "ok_pipeline"
    assert run.triggered_at is not None
    assert run.started_at is not None
