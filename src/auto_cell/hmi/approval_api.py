"""FastAPI endpoints for approvals, dashboard, and GMP identity/esignature."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.responses import RedirectResponse

from auto_cell._utils import validate_run_id
from auto_cell.audit.audit_log import AuditLog
from auto_cell.audit.ebr_report import build_ebr
from auto_cell.audit.event_store import EventWriter
from auto_cell.auth.db import UserDB
from auto_cell.auth.models import Token, User, UserInDB
from auto_cell.auth.security import create_access_token, get_current_user, oauth2_scheme
from auto_cell.hmi.approval_matrix import ApprovalMatrix
from auto_cell.hmi.approval_models import ApprovalRequest
from auto_cell.hmi.approval_service import ApprovalService
from auto_cell.hmi.approval_store import ApprovalStore, SqliteApprovalStore
from auto_cell.hmi.dashboard_service import DashboardService


class Services:
    def __init__(self, base_dir: Path, matrix_path: Path):
        self.event_writer = EventWriter(base_dir / "events")
        self.audit_log = AuditLog(base_dir / "audit")
        self.matrix = ApprovalMatrix(matrix_path)
        self.user_db = UserDB(base_dir / "auth" / "users.db")
        self.approval_store: ApprovalStore = SqliteApprovalStore(base_dir / "approvals.db")
        self.approval_service = ApprovalService(
            self.event_writer,
            self.audit_log,
            self.matrix,
            store=self.approval_store,
            user_db=self.user_db,
        )
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


def get_services() -> Services:
    if _services is None:
        raise RuntimeError("Services not initialized")
    return _services


def _validate_id(value: str) -> str:
    try:
        return validate_run_id(value)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


def _get_user_db() -> UserDB:
    return get_services().user_db


def current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    return get_current_user(token, _get_user_db())


# Optional auth for the landing page: redirect unauthenticated users to login.
_oauth2_scheme_optional = HTTPBearer(auto_error=False)


def current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_oauth2_scheme_optional),
) -> UserInDB | None:
    if credentials is None:
        return None
    try:
        return get_current_user(credentials.credentials, _get_user_db())
    except HTTPException:
        return None


class SignatureBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=512)
    pin: str = Field(..., min_length=1, max_length=64)
    meaning_of_signature: str = Field(..., min_length=1, max_length=512)


class ReviewBody(BaseModel):
    comments: str = Field(..., min_length=1, max_length=1024)


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@app.post("/hmi/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user_db = _get_user_db()
    user = user_db.authenticate(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.user_id, "role": user.role.value}
    )
    return Token(access_token=access_token)


@app.get("/hmi/auth/me", response_model=User)
async def read_current_user(user: UserInDB = Depends(current_user)) -> User:
    return User.model_validate(user)


@app.get("/hmi/login")
async def login_page(request: Request) -> Any:
    return templates.TemplateResponse(request, "login.html")


# ---------------------------------------------------------------------------
# Dashboard landing
# ---------------------------------------------------------------------------


@app.get("/hmi")
async def dashboard_page(
    request: Request,
    user: UserInDB | None = Depends(current_user_optional),
) -> Any:
    if user is None:
        return RedirectResponse(url="/hmi/login")
    return templates.TemplateResponse(request, "index.html")


# ---------------------------------------------------------------------------
# Run listing
# ---------------------------------------------------------------------------


@app.get("/hmi/runs")
async def list_runs(
    user: UserInDB = Depends(current_user),
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


# ---------------------------------------------------------------------------
# Approval endpoints
# ---------------------------------------------------------------------------


@app.get("/hmi/approvals/pending", response_model=list[ApprovalRequest])
async def list_pending(
    user: UserInDB = Depends(current_user),
) -> list[ApprovalRequest]:
    return get_services().approval_service.list_pending()


@app.get("/hmi/approvals/{request_id}", response_model=ApprovalRequest)
async def get_request(
    request_id: str,
    user: UserInDB = Depends(current_user),
) -> ApprovalRequest:
    _validate_id(request_id)
    req = get_services().approval_service.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="not found")
    return req


@app.post("/hmi/approvals/{request_id}/approve", response_model=ApprovalRequest)
async def approve(
    request_id: str,
    body: SignatureBody,
    user: UserInDB = Depends(current_user),
) -> ApprovalRequest:
    _validate_id(request_id)
    try:
        return get_services().approval_service.approve(
            request_id,
            user,
            body.pin,
            body.reason,
            body.meaning_of_signature,
        )
    except KeyError:
        raise HTTPException(status_code=404)
    except ValueError as e:
        detail = str(e)
        if detail == "invalid pin":
            raise HTTPException(status_code=401, detail=detail)
        raise HTTPException(status_code=409, detail=detail)


@app.post("/hmi/approvals/{request_id}/reject", response_model=ApprovalRequest)
async def reject(
    request_id: str,
    body: SignatureBody,
    user: UserInDB = Depends(current_user),
) -> ApprovalRequest:
    _validate_id(request_id)
    try:
        return get_services().approval_service.reject(
            request_id,
            user,
            body.pin,
            body.reason,
            body.meaning_of_signature,
        )
    except KeyError:
        raise HTTPException(status_code=404)
    except ValueError as e:
        detail = str(e)
        if detail == "invalid pin":
            raise HTTPException(status_code=401, detail=detail)
        raise HTTPException(status_code=409, detail=detail)


# ---------------------------------------------------------------------------
# Dashboard / EBR endpoints
# ---------------------------------------------------------------------------


@app.get("/hmi/runs/{run_id}/status")
async def run_status(
    run_id: str,
    user: UserInDB = Depends(current_user),
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
    user: UserInDB = Depends(current_user),
) -> list[dict[str, Any]]:
    _validate_id(run_id)
    return get_services().dashboard.run_trend(run_id, channel, start, end)


@app.get("/hmi/runs/{run_id}/events")
async def run_events(
    run_id: str,
    limit: int = Query(100, ge=1, le=1000),
    user: UserInDB = Depends(current_user),
) -> list[dict[str, Any]]:
    _validate_id(run_id)
    return get_services().dashboard.run_events(run_id, limit)


@app.get("/hmi/runs/{run_id}/ebr")
async def get_ebr(
    run_id: str,
    user: UserInDB = Depends(current_user),
) -> dict[str, Any]:
    _validate_id(run_id)
    svc = get_services()
    return build_ebr(svc.event_writer.base_dir, run_id, audit_base_dir=svc.audit_log.base_dir)


@app.post("/hmi/runs/{run_id}/audit_review")
async def create_audit_review(
    run_id: str,
    body: ReviewBody,
    user: UserInDB = Depends(current_user),
) -> dict[str, Any]:
    _validate_id(run_id)
    record = get_services().audit_log.review(run_id, user.user_id, body.comments)
    return record.model_dump(mode="json")


@app.get("/hmi/runs/{run_id}/audit_review")
async def list_audit_reviews(
    run_id: str,
    user: UserInDB = Depends(current_user),
) -> list[dict[str, Any]]:
    _validate_id(run_id)
    records = get_services().audit_log.load(run_id)
    return [
        r.model_dump(mode="json")
        for r in records
        if r.action == "audit_trail_reviewed"
    ]
