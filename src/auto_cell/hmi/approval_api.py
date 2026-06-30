"""FastAPI endpoints for approvals and dashboard."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from auto_cell._utils import validate_run_id
from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.event_store import EventWriter
from auto_cell.audit.ebr_report import build_ebr
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_service import ApprovalService, ApprovalRequest
from auto_cell.hmi.dashboard_service import DashboardService


class Services:
    def __init__(self, base_dir: Path, matrix_path: Path):
        self.event_writer = EventWriter(base_dir / "events")
        self.audit_log = AuditLog(base_dir / "audit")
        self.matrix = ApprovalMatrix(matrix_path)
        self.approval_service = ApprovalService(self.event_writer, self.audit_log, self.matrix)
        self.dashboard = DashboardService(self.event_writer)


_services: Services | None = None
_security = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _services
    if _services is None:
        base_dir = Path("data/event_store")
        matrix_path = Path("config/approval_matrix.yaml")
        _services = Services(base_dir, matrix_path)
    yield


app = FastAPI(title="auto_cell HMI API", lifespan=lifespan)

_STATIC_DIR = Path(__file__).parent / "static"
_TEMPLATE_DIR = Path(__file__).parent / "templates"

if _STATIC_DIR.exists():
    app.mount("/hmi/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


class DecisionBody(BaseModel):
    actor: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_:\-]+$")
    reason: str = Field(..., min_length=1, max_length=512)


def _require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> None:
    expected = os.getenv("HMI_API_KEY")
    # If no key is configured (Phase 1 dev convenience), skip authentication.
    if not expected:
        return
    if credentials is None or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="invalid or missing API key")


def get_services() -> Services:
    if _services is None:
        raise RuntimeError("Services not initialized")
    return _services


def _validate_id(value: str) -> str:
    try:
        return validate_run_id(value)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/hmi")
async def dashboard_page(request: Request) -> Any:
    return templates.TemplateResponse(request, "index.html")


@app.get("/hmi/runs")
async def list_runs(
    _api_key: None = Depends(_require_api_key),
) -> list[str]:
    """Return run IDs that have data in the event store."""
    base_dir = get_services().event_writer.base_dir
    run_ids: list[str] = []
    if not base_dir.exists():
        return run_ids
    for entry in base_dir.iterdir():
        if not entry.is_dir():
            continue
        try:
            validate_run_id(entry.name)
        except ValueError:
            continue
        run_ids.append(entry.name)
    return sorted(run_ids)


@app.get("/hmi/approvals/pending", response_model=list[ApprovalRequest])
async def list_pending(
    _api_key: None = Depends(_require_api_key),
) -> list[ApprovalRequest]:
    return get_services().approval_service.list_pending()


@app.get("/hmi/approvals/{request_id}", response_model=ApprovalRequest)
async def get_request(
    request_id: str,
    _api_key: None = Depends(_require_api_key),
) -> ApprovalRequest:
    _validate_id(request_id)
    req = get_services().approval_service.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="not found")
    return req


@app.post("/hmi/approvals/{request_id}/approve", response_model=ApprovalRequest)
async def approve(
    request_id: str,
    body: DecisionBody,
    _api_key: None = Depends(_require_api_key),
) -> ApprovalRequest:
    _validate_id(request_id)
    try:
        return get_services().approval_service.approve(request_id, body.actor, body.reason)
    except KeyError:
        raise HTTPException(status_code=404)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/hmi/approvals/{request_id}/reject", response_model=ApprovalRequest)
async def reject(
    request_id: str,
    body: DecisionBody,
    _api_key: None = Depends(_require_api_key),
) -> ApprovalRequest:
    _validate_id(request_id)
    try:
        return get_services().approval_service.reject(request_id, body.actor, body.reason)
    except KeyError:
        raise HTTPException(status_code=404)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/hmi/runs/{run_id}/status")
async def run_status(
    run_id: str,
    _api_key: None = Depends(_require_api_key),
) -> dict[str, Any]:
    _validate_id(run_id)
    svc = get_services()
    return svc.dashboard.run_status(run_id, svc.approval_service)


@app.get("/hmi/runs/{run_id}/trend")
async def run_trend(
    run_id: str,
    channel: str = Query(...),
    start: datetime | None = None,
    end: datetime | None = None,
    _api_key: None = Depends(_require_api_key),
) -> list[dict[str, Any]]:
    _validate_id(run_id)
    return get_services().dashboard.run_trend(run_id, channel, start, end)


@app.get("/hmi/runs/{run_id}/events")
async def run_events(
    run_id: str,
    limit: int = Query(100, ge=1, le=1000),
    _api_key: None = Depends(_require_api_key),
) -> list[dict[str, Any]]:
    _validate_id(run_id)
    return get_services().dashboard.run_events(run_id, limit)


@app.get("/hmi/runs/{run_id}/ebr")
async def get_ebr(
    run_id: str,
    _api_key: None = Depends(_require_api_key),
) -> dict[str, Any]:
    _validate_id(run_id)
    svc = get_services()
    return build_ebr(svc.event_writer.base_dir, run_id)
