import json
import secrets
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from scml.ai.runtime import explain
from scml.data.store import Store
from scml.domain.errors import DomainError
from scml.domain.schemas import (
    AnomalyRequest,
    DatasetSummary,
    Decision,
    DeploymentResponse,
    DeployRequest,
    ErrorResponse,
    ExplainRequest,
    ForecastRequest,
    JobResponse,
    MonitorRequest,
    MonitorResponse,
    NarrativeResponse,
    Page,
    PredictionResponse,
    RunDetail,
    RunSummary,
    ScheduleRequest,
    ScheduleResponse,
    Task,
    TrainRequest,
)
from scml.observability.logging import log
from scml.services.bootstrap import bootstrap
from scml.services.config import Settings
from scml.services.http_limits import BoundedBodyMiddleware
from scml.services.ingestion import MAX_BYTES
from scml.services.lifecycle import Lifecycle, public_dataset, public_run
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware


def create_app(settings=None, boot=True):
    settings = settings or Settings()
    service = Lifecycle(Store(settings.root))

    @asynccontextmanager
    async def lifespan(app):
        if boot:
            bootstrap(service)
        yield

    app = FastAPI(
        title="SupplyChain MLOps",
        version="0.1.0",
        lifespan=lifespan,
        responses={
            code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409, 413, 415, 422, 500)
        },
        description="Local model lifecycle. Reads are public on loopback; writes require role tokens and idempotency keys.",
    )
    app.state.service = service
    app.state.settings = settings
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "[::1]", "api", "testserver"],
    )

    app.add_middleware(BoundedBodyMiddleware)

    def error(request, status, code, message, details=None):
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "trace_id": getattr(request.state, "trace_id", "unknown"),
                    "details": details or [],
                }
            },
        )

    @app.middleware("http")
    async def telemetry(request, call_next):
        start = time.perf_counter()
        request.state.trace_id = uuid4().hex
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return error(request, 400, "invalid_length", "Invalid content length")
        if length > MAX_BYTES:
            return error(request, 413, "file_too_large", "Request exceeds 16 MiB")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
            if origin and origin != expected:
                return error(request, 403, "origin_denied", "Cross-origin writes are disabled")
        try:
            response = await call_next(request)
        except Exception as exc:
            log("request_failed", trace_id=request.state.trace_id, error_type=type(exc).__name__)
            response = error(
                request,
                500,
                "internal_error",
                "Unexpected server error; use the trace ID to investigate",
            )
        response.headers["X-Trace-ID"] = request.state.trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        log(
            "http_request",
            trace_id=request.state.trace_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency_ms=(time.perf_counter() - start) * 1000,
        )
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return error(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        details = [
            {"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()
        ]
        return error(request, 422, "validation", "Request validation failed", details)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(request, exc.status_code, "http_error", str(exc.detail))

    def identity(authorization: Annotated[str | None, Header()] = None):
        token = authorization.removeprefix("Bearer ") if authorization else ""
        for role, value in settings.tokens.items():
            if secrets.compare_digest(token, value):
                return role
        raise DomainError("Use a local workspace role token", "unauthorized", 401)

    def operator(actor=Depends(identity)):
        if actor != "operator":
            raise DomainError("Operator role required", "forbidden", 403)
        return actor

    def reviewer(actor=Depends(identity)):
        if actor != "reviewer":
            raise DomainError("Reviewer role required", "forbidden", 403)
        return actor

    def idem(idempotency_key: Annotated[str, Header(min_length=8, max_length=160)]):
        return idempotency_key

    def page(items, limit, offset):
        return Page(
            items=items[offset : offset + limit], total=len(items), limit=limit, offset=offset
        )

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/ready", tags=["health"])
    def ready():
        with service.store.connect(True) as db:
            db.execute("SELECT 1").fetchone()
        return {"status": "ready", "database": "ok"}

    @app.get("/api/v1/session", tags=["access"])
    def session(actor=Depends(identity)):
        return {"role": actor}

    @app.get("/api/v1/overview", tags=["read"])
    def overview():
        runs = service.store.rows("runs")
        datasets = service.store.rows("datasets")
        monitors = service.store.rows("monitors")
        jobs = service.store.rows("jobs")
        heartbeat = settings.root / "worker-heartbeat.json"
        worker = False
        if heartbeat.exists():
            try:
                worker = (
                    datetime.now(UTC)
                    - datetime.fromisoformat(json.loads(heartbeat.read_text())["at"])
                ).total_seconds() < 90
            except (ValueError, KeyError):
                pass
        return {
            "datasets": len(datasets),
            "accepted_records": sum(d["validation"]["accepted"] for d in datasets),
            "rejected_records": sum(d["validation"]["rejected"] for d in datasets),
            "runs": len(runs),
            "pending_approvals": sum(r["stage"] == "candidate" for r in runs),
            "deployments": {t: service.active(t) for t in ("forecast", "anomaly")},
            "latest_monitor": monitors[0] if monitors else None,
            "worker_online": worker,
            "active_jobs": sum(j["status"] in ("queued", "running") for j in jobs),
            "ai": {
                "enabled": settings.llm_enabled,
                "runtime": settings.llm_runtime,
                "model": settings.llm_model or None,
            },
            "latest_runs": [public_run(r) for r in runs[:8]],
        }

    @app.get("/api/v1/datasets", response_model=Page, tags=["read"])
    def datasets(
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
        q: str = Query("", max_length=160),
    ):
        return page(
            [
                public_dataset(d)
                for d in service.store.rows("datasets")
                if q.lower() in d["name"].lower()
            ],
            limit,
            offset,
        )

    @app.get("/api/v1/datasets/{ident}", response_model=DatasetSummary, tags=["read"])
    def dataset(ident: str):
        return public_dataset(service.require("datasets", ident))

    @app.get("/api/v1/datasets/{ident}/records", response_model=Page, tags=["read"])
    def dataset_records(
        ident: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)
    ):
        return page(service.require("datasets", ident)["records"], limit, offset)

    @app.get("/api/v1/datasets/{ident}/export", tags=["read"])
    def export_dataset(ident: str):
        ds = service.require("datasets", ident)
        return Response(
            "".join(json.dumps(r) + "\n" for r in ds["records"]),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": 'attachment; filename="validated-records.jsonl"'},
        )

    @app.post("/api/v1/datasets", response_model=DatasetSummary, tags=["mutation"], status_code=201)
    async def import_dataset(
        request: Request,
        filename: str = Query(..., max_length=200),
        actor=Depends(operator),
        key=Depends(idem),
    ):
        content_type = request.headers.get("content-type", "").split(";")[0]
        if content_type not in ("application/x-ndjson", "application/jsonl"):
            raise DomainError("Use application/x-ndjson for JSONL uploads", "unsupported_type", 415)
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BYTES:
                raise DomainError("Dataset exceeds 16 MiB", "file_too_large", 413)
            chunks.append(chunk)
        return service.ingest(b"".join(chunks), filename, actor, key)

    @app.get("/api/v1/runs", response_model=Page, tags=["read"])
    def runs(
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
        task: Task | None = None,
        stage: str | None = Query(None, max_length=20),
    ):
        return page(
            [
                public_run(r)
                for r in service.store.rows("runs")
                if (not task or r["task"] == task) and (not stage or r["stage"] == stage)
            ],
            limit,
            offset,
        )

    @app.get("/api/v1/runs/{ident}", response_model=RunDetail, tags=["read"])
    def run(ident: str):
        return service.require("runs", ident)

    @app.get("/api/v1/runs/{ident}/artifact", tags=["read"])
    def artifact(ident: str):
        item = service.require("runs", ident)
        service.verify_artifact(item)
        return Response(
            json.dumps(item["artifact"], indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="model.json"',
                "X-Artifact-SHA256": item["artifact_sha256"],
            },
        )

    @app.post("/api/v1/training", response_model=JobResponse, tags=["mutation"], status_code=202)
    def training(body: TrainRequest, actor=Depends(operator), key=Depends(idem)):
        return service.queue(body.model_dump(), actor, key)

    @app.get("/api/v1/jobs", response_model=Page, tags=["read"])
    def jobs(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)):
        return page(service.store.rows("jobs"), limit, offset)

    @app.get("/api/v1/jobs/{ident}", response_model=JobResponse, tags=["read"])
    def job(ident: str):
        return service.require("jobs", ident)

    @app.post("/api/v1/runs/{ident}/approve", response_model=RunSummary, tags=["mutation"])
    def approve(ident: str, body: Decision, actor=Depends(reviewer), key=Depends(idem)):
        return service.approve(ident, body.reason, actor, key)

    @app.post("/api/v1/deployments/{task}", response_model=DeploymentResponse, tags=["mutation"])
    def deploy(task: Task, body: DeployRequest, actor=Depends(operator), key=Depends(idem)):
        return service.deploy(task, body.run_id, body.expected_current, body.reason, actor, key)

    @app.post(
        "/api/v1/deployments/{task}/rollback", response_model=DeploymentResponse, tags=["mutation"]
    )
    def rollback(task: Task, body: DeployRequest, actor=Depends(operator), key=Depends(idem)):
        return service.deploy(
            task, body.run_id, body.expected_current, body.reason, actor, key, rollback=True
        )

    @app.post("/api/v1/predictions/forecast", response_model=PredictionResponse, tags=["mutation"])
    def forecast(body: ForecastRequest, actor=Depends(operator), key=Depends(idem)):
        return service.infer("forecast", body.model_dump(mode="json"), actor, key)

    @app.post("/api/v1/predictions/anomaly", response_model=PredictionResponse, tags=["mutation"])
    def anomaly(body: AnomalyRequest, actor=Depends(operator), key=Depends(idem)):
        return service.infer("anomaly", body.model_dump(mode="json"), actor, key)

    @app.get("/api/v1/predictions", response_model=Page, tags=["read"])
    def predictions(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)):
        return page(service.store.rows("predictions"), limit, offset)

    @app.get("/api/v1/monitors", response_model=Page, tags=["read"])
    def monitors(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)):
        return page(service.store.rows("monitors"), limit, offset)

    @app.post("/api/v1/monitors", response_model=MonitorResponse, tags=["mutation"])
    def monitor(body: MonitorRequest, actor=Depends(operator), key=Depends(idem)):
        return service.monitor(body.task, body.dataset_id, actor, key)

    @app.get("/api/v1/schedules", response_model=Page, tags=["read"])
    def schedules(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)):
        return page(service.store.rows("schedules"), limit, offset)

    @app.post("/api/v1/schedules", response_model=ScheduleResponse, tags=["mutation"])
    def schedule(body: ScheduleRequest, actor=Depends(operator), key=Depends(idem)):
        return service.schedule(body.model_dump(), actor, key)

    @app.post(
        "/api/v1/schedules/{ident}/enabled", response_model=ScheduleResponse, tags=["mutation"]
    )
    def toggle(ident: str, enabled: bool, actor=Depends(operator), key=Depends(idem)):
        return service.set_schedule(ident, enabled, actor, key)

    @app.get("/api/v1/events", response_model=Page, tags=["read"])
    def events(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)):
        return page(service.store.rows("events"), limit, offset)

    @app.post("/api/v1/runs/{ident}/explain", response_model=NarrativeResponse, tags=["narrative"])
    def narrative(ident: str, body: ExplainRequest, actor=Depends(identity)):
        run = service.require("runs", ident)
        evidence = {
            ident: {
                "task": run["task"],
                "metrics": run["metrics"],
                "gate": run["gate"],
                "dataset_fingerprint": run["dataset_fingerprint"],
            }
        }
        return explain(settings, evidence, body.model)

    return app


app = create_app()
