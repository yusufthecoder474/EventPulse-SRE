import asyncio
import csv
import io
import json
import logging
import os
import re
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .database import connect, Event, Registration, Incident
from .telemetry import Telemetry

logger = logging.getLogger("eventpulse")
logging.basicConfig(level=logging.INFO, format="%(message)s")


class RegistrationInput(BaseModel):
    event_id: int = Field(gt=0)
    email: str = Field(min_length=5, max_length=160)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("A valid email address is required")
        return value


class FaultInput(BaseModel):
    kind: Literal["none", "latency", "http500", "dependency", "database", "warning"]
    duration_seconds: int = Field(default=15, ge=1, le=120)
    delay_ms: int = Field(default=750, ge=0, le=3000)
    every: int = Field(default=1, ge=1, le=100)


class NoteInput(BaseModel):
    notes: str = Field(max_length=2000)


def create_app(url=None, fault_enabled=None, window=None):
    telemetry = Telemetry(window or int(os.getenv("OBSERVATION_WINDOW_SECONDS", "60")))
    if not 2 <= telemetry.window <= 3600:
        raise ValueError("Observation window must be 2..3600 seconds")
    enabled = fault_enabled if fault_enabled is not None else os.getenv("ENABLE_FAULTS") == "true"
    if enabled and os.getenv("APP_ENV", "local") != "local":
        raise RuntimeError("Fault injection is only permitted in APP_ENV=local")
    token = os.getenv("FAULT_TOKEN", "")
    if enabled and len(token) < 24:
        raise RuntimeError("Set a local FAULT_TOKEN of at least 24 characters")
    engine, factory = connect(url)
    fault = {"kind": "none", "expires": 0, "delay_ms": 0, "every": 1, "seen": 0}
    pending = {}

    def current_fault():
        if time.time() >= fault["expires"]:
            fault["kind"] = "none"
        return fault["kind"]

    def ready():
        try:
            with engine.connect() as db:
                db.execute(text("SELECT 1"))
            value = current_fault() != "database"
        except SQLAlchemyError:
            value = False
        telemetry.ready.set(int(value))
        return value

    def evaluate():
        summary = telemetry.summary()
        enough = summary["requests"] >= 5
        flags = {"availability": enough and summary["error_rate"] > 0.05, "latency": enough and summary["p95"] > 0.5}
        now = time.time()
        with factory.begin() as db:
            for kind, firing in flags.items():
                existing = db.scalar(select(Incident).where(Incident.kind == kind, Incident.end.is_(None)))
                if firing:
                    pending.setdefault(kind, now)
                    if now - pending[kind] >= 1 and existing is None:
                        metric = summary["error_rate"] if kind == "availability" else summary["p95"]
                        affected = [
                            e["route"] for e in summary["endpoints"] if e["requests"] and (e["error_rate"] > 0.05 if kind == "availability" else e["p95"] > 0.5)
                        ]
                        db.add(
                            Incident(
                                id=str(uuid.uuid4()),
                                kind=kind,
                                severity="SEV2" if kind == "availability" else "SEV3",
                                start=now,
                                evidence={
                                    "metric": metric,
                                    "requests": summary["requests"],
                                    "window_seconds": telemetry.window,
                                    "endpoints": affected,
                                    "detector": "local-window-v1",
                                },
                                timeline=[{"at": now, "action": "firing", "detail": "User-impact threshold sustained for 1 second"}],
                                notes="",
                            )
                        )
                else:
                    pending.pop(kind, None)
                    if existing:
                        existing.end = now
                        existing.timeline = [
                            *existing.timeline,
                            {"at": now, "action": "resolved", "detail": "Threshold cleared or insufficient recent traffic; verify recovery with new probes"},
                        ]
        return summary

    async def monitor():
        while True:
            try:
                await asyncio.to_thread(ready)
                await asyncio.to_thread(evaluate)
            except SQLAlchemyError:
                logger.error(json.dumps({"event": "monitor_database_unavailable"}))
            await asyncio.sleep(0.5)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(monitor())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        engine.dispose()

    app = FastAPI(title="EventPulse SRE", version="1.0.0", lifespan=lifespan)
    app.state.telemetry, app.state.factory, app.state.evaluate = telemetry, factory, evaluate
    app.state.engine = engine

    @app.middleware("http")
    async def instrument(request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        correlation = supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", supplied) else uuid.uuid4().hex
        start = time.perf_counter()
        telemetry.inflight.inc()
        try:
            kind = current_fault()
            business = request.url.path == "/events" or request.url.path.startswith("/registrations")
            if business:
                fault["seen"] += 1
            affected = business and fault["seen"] % fault["every"] == 0
            if affected and kind in ("latency", "dependency"):
                await asyncio.sleep(fault["delay_ms"] / 1000)
            if affected and kind in ("http500", "database", "dependency"):
                status = {"http500": 500, "database": 503, "dependency": 504}[kind]
                response = JSONResponse({"error": "Injected local fault", "request_id": correlation}, status_code=status)
            else:
                if business and kind == "warning":
                    logger.warning(json.dumps({"event": "synthetic_warning", "request_id": correlation, "user_impact": False}))
                response = await call_next(request)
        except Exception:
            logger.exception(json.dumps({"event": "unhandled_error", "request_id": correlation}))
            response = JSONResponse({"error": "Internal server error", "request_id": correlation}, status_code=500)
        finally:
            telemetry.inflight.dec()
        duration = time.perf_counter() - start
        route = getattr(request.scope.get("route"), "path", "/unmatched")
        if business and route == "/unmatched":
            route = (
                "/events" if request.url.path == "/events" else "/registrations" if request.url.path == "/registrations" else "/registrations/{registration_id}"
            )
        telemetry.record(request.method, route, response.status_code, duration)
        if request.method == "POST" and route == "/registrations":
            outcome = "success" if response.status_code == 201 else "replayed" if response.status_code == 200 else "failure"
            telemetry.registrations.labels(outcome).inc()
        telemetry.uptime.set(time.time() - telemetry.started)
        response.headers["X-Request-ID"] = correlation
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "request_id": correlation,
                    "method": request.method,
                    "route": route,
                    "status": response.status_code,
                    "duration_seconds": duration,
                }
            )
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            {"error": "Invalid input", "fields": [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]}, status_code=422
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        return JSONResponse({"error": "Database unavailable"}, status_code=503)

    @app.get("/health/live")
    def live():
        return {"status": "alive", "version": "1.0.0"}

    @app.get("/health/ready")
    def readiness():
        value = ready()
        return JSONResponse({"database_ready": value}, status_code=200 if value else 503)

    @app.get("/events")
    def events():
        with factory() as db:
            return [{"id": e.id, "name": e.name, "capacity": e.capacity, "booked": e.booked} for e in db.scalars(select(Event).order_by(Event.id))]

    @app.post("/registrations", status_code=201)
    def register(body: RegistrationInput, idempotency_key: str = Header(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")):
        def existing_response(existing):
            if existing.event_id != body.event_id or existing.email != body.email:
                raise HTTPException(409, "Idempotency key belongs to a different request")
            return JSONResponse({"id": existing.id, "event_id": existing.event_id, "email": existing.email}, status_code=200)

        try:
            with factory.begin() as db:
                existing = db.scalar(select(Registration).where(Registration.key == idempotency_key))
                if existing:
                    return existing_response(existing)
                event = db.get(Event, body.event_id)
                if not event:
                    raise HTTPException(404, "Event not found")
                # Conditional UPDATE locks the row and prevents overselling, including concurrent requests.
                changed = db.execute(update(Event).where(Event.id == body.event_id, Event.booked < Event.capacity).values(booked=Event.booked + 1))
                if changed.rowcount != 1:
                    raise HTTPException(409, "Event capacity reached")
                registration = Registration(id=str(uuid.uuid4()), event_id=body.event_id, email=body.email, key=idempotency_key)
                db.add(registration)
                db.flush()
                result = {"id": registration.id, "event_id": registration.event_id, "email": registration.email}

            return result
        except IntegrityError:
            with factory() as db:
                existing = db.scalar(select(Registration).where(Registration.key == idempotency_key))
                if existing:
                    return existing_response(existing)

            raise HTTPException(409, "Email already registered for this event") from None
        except HTTPException:
            raise
        except SQLAlchemyError:
            raise

    @app.get("/registrations/{registration_id}")
    def registration(registration_id: str):
        with factory() as db:
            item = db.get(Registration, registration_id)
            if not item:
                raise HTTPException(404, "Registration not found")
            return {"id": item.id, "event_id": item.event_id, "email": item.email}

    @app.get("/metrics")
    def metrics():
        ready()
        telemetry.uptime.set(time.time() - telemetry.started)
        return Response(generate_latest(telemetry.registry), media_type=CONTENT_TYPE_LATEST)

    @app.get("/operations/summary")
    def summary():
        data = telemetry.summary()
        data["database_ready"] = ready()
        with factory() as db:
            data["active_incidents"] = len(list(db.scalars(select(Incident).where(Incident.end.is_(None)))))
        data.update(
            {
                "faults_enabled": enabled,
                "fault": current_fault(),
                "status": "no traffic" if data["requests"] == 0 else "degraded" if data["error_rate"] > 0.05 or data["p95"] > 0.5 else "operational",
            }
        )
        return data

    @app.get("/operations/incidents")
    def incidents():
        with factory() as db:
            return [
                {
                    "id": i.id,
                    "kind": i.kind,
                    "severity": i.severity,
                    "start": i.start,
                    "end": i.end,
                    "evidence": i.evidence,
                    "timeline": i.timeline,
                    "notes": i.notes,
                    "status": "resolved" if i.end else "firing",
                }
                for i in db.scalars(select(Incident).order_by(Incident.start.desc()).limit(100))
            ]

    def authorize(request, supplied):
        if not enabled:
            raise HTTPException(403, "Fault lab disabled; opt in locally")
        if request.client.host not in ("127.0.0.1", "::1", "testclient"):
            raise HTTPException(403, "Loopback clients only")
        if request.headers.get("origin") and request.headers["origin"] not in (
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ):
            raise HTTPException(403, "Untrusted origin")
        if not secrets.compare_digest(supplied or "", token):
            raise HTTPException(403, "Local lab token required")

    @app.post("/operations/faults")
    def inject(body: FaultInput, request: Request, x_lab_token: str = Header(default="")):
        authorize(request, x_lab_token)
        fault.update({"kind": body.kind, "expires": time.time() + body.duration_seconds, "delay_ms": body.delay_ms, "every": body.every, "seen": 0})
        logger.info(json.dumps({"event": "fault_configuration", "kind": body.kind, "duration_seconds": body.duration_seconds}))
        return {"kind": current_fault(), "expires": fault["expires"]}

    @app.patch("/operations/incidents/{incident_id}")
    def note(incident_id: str, body: NoteInput, request: Request, x_lab_token: str = Header(default="")):
        authorize(request, x_lab_token)
        with factory.begin() as db:
            incident = db.get(Incident, incident_id)
            if not incident:
                raise HTTPException(404, "Incident not found")
            incident.notes = body.notes
            incident.timeline = [*incident.timeline, {"at": time.time(), "action": "note updated", "detail": body.notes}]
        return {"saved": True}

    @app.get("/operations/experiments")
    def experiments(format: Literal["json", "csv"] = "json"):
        path = Path(os.getenv("EVIDENCE_PATH", "evidence/experiments.json"))
        data = json.loads(path.read_text()) if path.exists() else {"runs": [], "summary": {}, "source": "No experiments run. Run scripts/evaluate.py."}
        if format == "json":
            return data
        stream = io.StringIO()
        runs = data.get("runs", [])
        writer = csv.DictWriter(stream, fieldnames=list(runs[0]) if runs else ["scenario"])
        writer.writeheader()
        writer.writerows(runs)
        return Response(stream.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=experiments.csv"})

    return app
