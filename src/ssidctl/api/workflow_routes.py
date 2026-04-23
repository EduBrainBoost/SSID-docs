"""Workflow Engine API — FastAPI router for durable workflow run management.

Endpoints:
  GET  /api/ops/workflows/runs               — List all workflow runs
  GET  /api/ops/workflows/runs/{run_id}      — Run detail + step history
  POST /api/ops/workflows/runs/{run_id}/resume — Resume a blocked/failed run
  POST /api/ops/workflows/runs/{run_id}/cancel — Cancel a run

All responses are JSON.
Error handling: 404 if run not found, 400 on engine errors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from fastapi import APIRouter, HTTPException

    _FASTAPI_AVAILABLE = True
except ImportError:
    APIRouter = None  # type: ignore[assignment,misc]
    _FASTAPI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------


def create_workflow_router(state_dir: Path) -> APIRouter | None:
    """Create the workflow engine API router.

    Args:
        state_dir: Base state directory; workflow store lives at
                   ``state_dir / "workflows"``.

    Returns:
        FastAPI APIRouter with /api/ops/workflows routes, or None if FastAPI
        is not installed in the current environment.
    """
    if not _FASTAPI_AVAILABLE:
        return None

    router = APIRouter(prefix="/api/ops/workflows", tags=["workflows"])

    def _get_engine():  # type: ignore[return]
        """Instantiate store + engine on each request (stateless per-call)."""
        from ssidctl.workflow.engine import WorkflowEngine
        from ssidctl.workflow.store import WorkflowStore

        store = WorkflowStore(state_dir / "workflows")
        engine = WorkflowEngine(store)
        return engine

    # -----------------------------------------------------------------------
    # GET /runs
    # -----------------------------------------------------------------------

    @router.get("/runs", response_model=list[dict[str, Any]])
    def list_runs() -> list[dict[str, Any]]:
        """Return all workflow runs.

        Response 200: list of run dicts (see WorkflowRun.to_dict())
        """
        engine = _get_engine()
        runs = engine.store.list_runs()
        return [run.to_dict() for run in runs]

    # -----------------------------------------------------------------------
    # GET /runs/{run_id}
    # -----------------------------------------------------------------------

    @router.get("/runs/{run_id}", response_model=dict[str, Any])
    def get_run(run_id: str) -> dict[str, Any]:
        """Return a single workflow run with its full step history.

        Response 200: run dict (see WorkflowRun.to_dict())
        Response 404: {"detail": "Workflow run not found: <run_id>"}
        """
        engine = _get_engine()
        run = engine.store.get_run(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow run not found: {run_id}",
            )
        return run.to_dict()

    # -----------------------------------------------------------------------
    # POST /runs/{run_id}/resume
    # -----------------------------------------------------------------------

    @router.post("/runs/{run_id}/resume", response_model=dict[str, Any])
    def resume_run(run_id: str) -> dict[str, Any]:
        """Resume a blocked or failed workflow run.

        Response 200: updated run dict
        Response 404: {"detail": "Workflow run not found: <run_id>"}
        Response 400: {"detail": "<engine error message>"}
        """
        from ssidctl.workflow.engine import EngineError

        engine = _get_engine()
        run = engine.store.get_run(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow run not found: {run_id}",
            )
        try:
            updated_run = engine.resume(run_id)
        except EngineError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return updated_run.to_dict()

    # -----------------------------------------------------------------------
    # POST /runs/{run_id}/cancel
    # -----------------------------------------------------------------------

    @router.post("/runs/{run_id}/cancel", response_model=dict[str, Any])
    def cancel_run(run_id: str) -> dict[str, Any]:
        """Cancel a workflow run.

        Response 200: updated run dict
        Response 404: {"detail": "Workflow run not found: <run_id>"}
        Response 400: {"detail": "<engine error message>"}
        """
        from ssidctl.workflow.engine import EngineError

        engine = _get_engine()
        run = engine.store.get_run(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow run not found: {run_id}",
            )
        try:
            updated_run = engine.cancel(run_id)
        except EngineError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return updated_run.to_dict()

    return router
