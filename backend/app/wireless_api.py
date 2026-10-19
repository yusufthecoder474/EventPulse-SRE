"""Guest-isolated offline WirelessLab routes; no capture/device/network operations."""

import hashlib
import io
import csv
import json
import logging
import os
from pathlib import Path
import secrets
import shutil
import sys
import threading
import time
import uuid

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from prometheus_client import Counter, Histogram
from sqlalchemy import String, Float, Integer, JSON, select, update, delete, func
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

LAB_ROOT = Path(os.getenv("WIRELESS_LAB_ROOT", str(Path(__file__).resolve().parents[2] / "wireless-lab"))).resolve()
sys.path.insert(0, str(LAB_ROOT / "python"))
from wirelesslab.scenarios import definitions, run_scenario, approved_capture  # noqa: E402
from wirelesslab.analyze import AnalyzerUnavailable, analyze_events, binary_path  # noqa: E402
from wirelesslab.packets import CaptureUnavailable, parse_capture, MAX_BYTES  # noqa: E402

logger = logging.getLogger("eventpulse.wireless")


class Guest(Base):
    __tablename__ = "wireless_guests"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires: Mapped[float] = mapped_column(Float)
    quota_start: Mapped[float] = mapped_column(Float)
    quota_count: Mapped[int] = mapped_column(Integer, default=0)


class WirelessRun(Base):
    __tablename__ = "wireless_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(64), index=True)
    created: Mapped[float] = mapped_column(Float)
    result: Mapped[dict] = mapped_column(JSON)


class VirtualAP(Base):
    __tablename__ = "wireless_aps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(40))
    ssid: Mapped[str] = mapped_column(String(32))
    bssid: Mapped[str] = mapped_column(String(17))
    channel: Mapped[int] = mapped_column(Integer)


class RunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(pattern="^[A-J]$")


class APInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9 _-]+$")
    ssid: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9 _-]+$")
    channel: int = Field(ge=1, le=165)


def install_wireless(app, engine, factory, registry):
    Base.metadata.create_all(engine)
    router = APIRouter(prefix="/wireless-lab", tags=["WirelessLab — synthetic offline demo"])
    guard = threading.Lock()
    execution_slots = threading.BoundedSemaphore(4)
    admissions = {}
    counter = Counter("wirelesslab_runs", "Completed safe scenario runs", ["scenario", "verdict"], registry=registry)
    duration = Histogram("wirelesslab_analysis_seconds", "Python-to-C++ analysis request duration", registry=registry)
    event_counter = Counter("wirelesslab_events", "Normalized events processed", registry=registry)
    configured_origins = {o.strip() for o in os.getenv("WIRELESS_ALLOWED_ORIGINS", "").split(",") if o.strip()}
    local_origins = {f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (5173, 8080, 8000)}

    def mutation(request: Request):
        origin = request.headers.get("origin")
        if request.headers.get("x-wireless-demo") != "1" or (origin and origin not in local_origins | configured_origins):
            raise HTTPException(403, "Demo mutation requires the approved same-origin client")

    def cleanup(db):
        expired = list(db.scalars(select(Guest.id).where(Guest.expires < time.time())))
        if expired:
            db.execute(delete(WirelessRun).where(WirelessRun.owner.in_(expired)))
            db.execute(delete(VirtualAP).where(VirtualAP.owner.in_(expired)))
            db.execute(delete(Guest).where(Guest.id.in_(expired)))

    def session(request: Request):
        token = request.cookies.get("wl_guest", "")
        if not token or len(token) > 100:
            raise HTTPException(401, "Continue as Guest to create a demo session")
        owner = hashlib.sha256(token.encode()).hexdigest()
        with factory() as db:
            guest = db.get(Guest, owner)
            if not guest or guest.expires < time.time():
                raise HTTPException(401, "Demo session expired; continue as guest again")
        return owner

    def quota(owner):
        now = time.time()
        with factory.begin() as db:
            reset = db.execute(update(Guest).where(Guest.id == owner, Guest.quota_start < now - 60).values(quota_start=now, quota_count=1))
            if reset.rowcount != 1:
                changed = db.execute(update(Guest).where(Guest.id == owner, Guest.quota_count < 12).values(quota_count=Guest.quota_count + 1))
                if changed.rowcount != 1:
                    raise HTTPException(429, "Demo execution limit: 12 operations per minute")

    def save(owner, result):
        identifier = str(uuid.uuid4())
        created = time.time()
        with factory.begin() as db:
            old = list(db.scalars(select(WirelessRun).where(WirelessRun.owner == owner).order_by(WirelessRun.created)))
            for row in old[:-19] if len(old) >= 20 else []:
                db.delete(row)
            db.add(WirelessRun(id=identifier, owner=owner, created=created, result=result))
        logger.info(
            json.dumps(
                {
                    "event": "wireless_demo_run",
                    "run_id": identifier,
                    "scenario": result.get("scenario", {}).get("id", "upload"),
                    "verdict": result.get("verdict", "analysis"),
                }
            )
        )
        return {"id": identifier, "created_at": created, **result}

    @router.get("/capabilities")
    def capabilities():
        return {
            "mode": "offline synthetic laboratory",
            "cpp_analyzer": binary_path().is_file(),
            "tshark": bool(shutil.which("tshark")),
            "hardware_integration": False,
            "live_capture": False,
            "wpa3_hardware_verified": False,
            "uploads_enabled": False,
            "guest_limits": {"session_seconds": 3600, "runs_retained": 20, "operations_per_minute": 12},
            "notice": "Packet fixtures are generated; event fixtures are simulations. No Cisco hardware or crypto verification.",
        }

    @router.post("/guest", status_code=201, dependencies=[Depends(mutation)])
    def create_guest(request: Request, response: Response):
        now = time.time()
        peer = hashlib.sha256((request.client.host if request.client else "unknown").encode()).hexdigest()
        with guard:
            for key in list(admissions):
                if now - admissions[key][0] > 60:
                    del admissions[key]
            start, count = admissions.get(peer, (now, 0))
            if count >= 10:
                raise HTTPException(429, "Too many demo-session requests; wait one minute")
            if len(admissions) >= 128 and peer not in admissions:
                raise HTTPException(429, "Demo admission capacity reached")
            admissions[peer] = (start, count + 1)
            with factory.begin() as db:
                cleanup(db)
                if db.scalar(select(func.count()).select_from(Guest)) >= 128:
                    raise HTTPException(429, "Demo session capacity reached")
                token = secrets.token_urlsafe(32)
                owner = hashlib.sha256(token.encode()).hexdigest()
                db.add(Guest(id=owner, expires=now + 3600, quota_start=now, quota_count=0))
                for index, (name, channel) in enumerate([("Atrium AP", 6), ("Engineering AP", 36), ("Library AP", 11)], 1):
                    db.add(VirtualAP(id=str(uuid.uuid4()), owner=owner, name=name, ssid="EventPulse-Lab", bssid=f"02:00:00:00:01:{index:02x}", channel=channel))
        response.set_cookie("wl_guest", token, httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=3600, path="/")
        response.headers["Cache-Control"] = "no-store"
        return {"mode": "guest", "label": "Demo Mode", "expires_at": now + 3600, "capabilities": capabilities()}

    @router.get("/session")
    def read_session(owner=Depends(session)):
        with factory() as db:
            return {"mode": "guest", "label": "Demo Mode", "expires_at": db.get(Guest, owner).expires}

    @router.delete("/session", dependencies=[Depends(mutation)])
    def clear_session(response: Response, owner=Depends(session)):
        with factory.begin() as db:
            db.execute(delete(WirelessRun).where(WirelessRun.owner == owner))
            db.execute(delete(VirtualAP).where(VirtualAP.owner == owner))
            db.execute(delete(Guest).where(Guest.id == owner))
        response.delete_cookie("wl_guest", path="/")
        return {"deleted": True}

    @router.get("/aps")
    def aps(owner=Depends(session)):
        with factory() as db:
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "ssid": a.ssid,
                    "channel": a.channel,
                    "bssid": a.bssid,
                    "status": "simulated online",
                    "source": "guest synthetic inventory, not a device probe",
                }
                for a in db.scalars(select(VirtualAP).where(VirtualAP.owner == owner).order_by(VirtualAP.name))
            ]

    @router.post("/aps", status_code=201, dependencies=[Depends(mutation)])
    def register_ap(body: APInput, owner=Depends(session)):
        quota(owner)
        with factory.begin() as db:
            if len(list(db.scalars(select(VirtualAP.id).where(VirtualAP.owner == owner)))) >= 8:
                raise HTTPException(409, "At most eight virtual APs per guest")
            identifier = str(uuid.uuid4())
            db.add(
                VirtualAP(
                    id=identifier,
                    owner=owner,
                    name=body.name,
                    ssid=body.ssid,
                    bssid="02:" + ":".join(secrets.token_hex(5)[i : i + 2] for i in range(0, 10, 2)),
                    channel=body.channel,
                )
            )
        return {"id": identifier, "mode": "simulated; no device configuration was changed"}

    @router.get("/scenarios")
    def list_scenarios(owner=Depends(session)):
        return definitions()

    @router.get("/fixtures")
    def fixtures(owner=Depends(session)):
        return [{"id": d["id"], "file": d["fixture"], "evidence_type": d["evidence_type"], "origin": d["origin"]} for d in definitions()]

    @router.post("/runs", status_code=201, dependencies=[Depends(mutation)])
    def run(body: RunInput, owner=Depends(session)):
        quota(owner)
        if not execution_slots.acquire(blocking=False):
            raise HTTPException(429, "Demo execution capacity reached")
        start = time.perf_counter()
        try:
            result = run_scenario(body.scenario_id)
        except (AnalyzerUnavailable, CaptureUnavailable) as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            execution_slots.release()
        counter.labels(body.scenario_id, result["verdict"]).inc()
        duration.observe(time.perf_counter() - start)
        event_counter.inc(len(result["events"]))
        return save(owner, result)

    @router.get("/runs")
    def runs(owner=Depends(session)):
        with factory() as db:
            return [
                {
                    "id": r.id,
                    "created_at": r.created,
                    "scenario_id": r.result.get("scenario", {}).get("id", "upload"),
                    "title": r.result.get("scenario", {}).get("title", "Authorized upload"),
                    "verdict": r.result.get("verdict", "analysis"),
                    "classifications": r.result.get("actual_classifications", []),
                    "duration_ms": r.result.get("total_duration_ms"),
                }
                for r in db.scalars(select(WirelessRun).where(WirelessRun.owner == owner).order_by(WirelessRun.created.desc()))
            ]

    def owned_run(identifier, owner):
        with factory() as db:
            item = db.get(WirelessRun, identifier)
            if not item or item.owner != owner:
                raise HTTPException(404, "Demo run not found")
            return {"id": item.id, "created_at": item.created, **item.result}

    @router.get("/runs/{run_id}")
    def read_run(run_id: str, owner=Depends(session)):
        return owned_run(run_id, owner)

    @router.get("/runs/{run_id}/events")
    def read_events(run_id: str, owner=Depends(session)):
        return owned_run(run_id, owner)["events"]

    @router.get("/runs/{run_id}/export")
    def export(run_id: str, format: str = "json", owner=Depends(session)):
        data = owned_run(run_id, owner)
        if format == "json":
            return JSONResponse(data, headers={"Content-Disposition": "attachment; filename=wireless-investigation.json", "Cache-Control": "no-store"})
        if format != "csv":
            raise HTTPException(422, "Export format must be json or csv")
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=["event_id", "timestamp_us", "client", "ap", "kind", "code", "origin", "link_layer"])
        writer.writeheader()
        for event in data["events"]:
            writer.writerow({k: event.get(k) for k in writer.fieldnames})
        return Response(
            buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=wireless-events.csv", "Cache-Control": "no-store"}
        )

    @router.get("/clients")
    def clients(owner=Depends(session)):
        output = {}
        with factory() as db:
            for row in db.scalars(select(WirelessRun).where(WirelessRun.owner == owner).order_by(WirelessRun.created)):
                for item in row.result.get("analysis", {}).get("clients", []):
                    output[item["client"] + "@" + item["ap"]] = {**item, "run_id": row.id, "source": "synthetic fixture observation"}
        return list(output.values())

    @router.get("/fixtures/{fixture_id}/capture")
    def capture(fixture_id: str, owner=Depends(session)):
        try:
            path = approved_capture(fixture_id)
        except ValueError as exc:
            raise HTTPException(404, "Approved packet fixture not found") from exc
        return Response(path.read_bytes(), media_type="application/vnd.tcpdump.pcap", headers={"Content-Disposition": f"attachment; filename={path.name}"})

    @router.post("/uploads", dependencies=[Depends(mutation)])
    async def upload(request: Request, owner=Depends(session)):
        # Never available to an ordinary guest. Requires explicit local operator opt-in and secret.
        expected = os.getenv("WIRELESS_UPLOAD_TOKEN", "")
        if (
            os.getenv("WIRELESS_ALLOW_UPLOADS") != "true"
            or len(expected) < 24
            or request.client.host not in ("127.0.0.1", "::1", "testclient")
            or not secrets.compare_digest(request.headers.get("x-wireless-upload-token", ""), expected)
        ):
            raise HTTPException(403, "Guest uploads are disabled; local authorized-lab operator only")
        if request.headers.get("x-lab-authorized") != "true":
            raise HTTPException(403, "Explicit authorized laboratory data declaration required")
        quota(owner)
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(413, "Capture exceeds 1 MiB limit")
            chunks.append(chunk)
        try:
            extraction = await __import__("asyncio").to_thread(parse_capture, b"".join(chunks), request.headers.get("x-file-name", "capture.pcap"), True)
            analysis = await __import__("asyncio").to_thread(analyze_events, extraction["events"])
        except (AnalyzerUnavailable, CaptureUnavailable) as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        result = {
            "scenario": {"id": "local-upload", "title": "Authorized, pseudonymized local capture", "evidence_type": "authorized_capture"},
            "events": extraction.pop("events"),
            "analysis": analysis,
            "extraction": extraction,
            "actual_classifications": sorted({c["classification"] for c in analysis["clients"]}),
            "verdict": "analysis_only",
            "mode": "local operator; metadata only; no raw capture retained",
        }
        return save(owner, result)

    app.include_router(router)
