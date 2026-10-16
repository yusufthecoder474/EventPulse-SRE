import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import create_app
from app.database import Event, Registration
from app.telemetry import calculate, percentile

TOKEN = "unit-test-token-only-00000000"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("FAULT_TOKEN", TOKEN)
    return create_app(f"sqlite:///{tmp_path}/test.db", fault_enabled=True, window=2)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


def post(client, key="request-key-1", email="student@example.test", event=1):
    return client.post("/registrations", json={"event_id": event, "email": email}, headers={"Idempotency-Key": key})


def inject(client, kind, **kwargs):
    return client.post("/operations/faults", json={"kind": kind, **kwargs}, headers={"X-Lab-Token": TOKEN})


def test_health_and_events(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").json()["database_ready"]
    assert len(client.get("/events").json()) == 3


def test_registration_round_trip(client):
    response = post(client)
    assert response.status_code == 201
    assert client.get("/registrations/" + response.json()["id"]).json() == response.json()
    assert client.get("/events").json()[0]["booked"] == 1


def test_replay_does_not_consume_capacity(client):
    first = post(client)
    second = post(client)
    assert second.status_code == 200
    assert first.json() == second.json()
    assert client.get("/events").json()[0]["booked"] == 1


def test_duplicate_email_rolls_back_capacity(client):
    post(client)
    assert post(client, key="different-key").status_code == 409
    assert client.get("/events").json()[0]["booked"] == 1


def test_key_payload_conflict(client):
    post(client)
    assert post(client, email="other@example.test").status_code == 409


@pytest.mark.parametrize("email", ["bad", "missing@domain", "a b@example.test", "@example.test"])
def test_invalid_email(client, email):
    assert post(client, email=email).status_code == 422


def test_missing_key_and_event(client):
    assert client.post("/registrations", json={"event_id": 1, "email": "a@b.test"}).status_code == 422
    assert post(client, event=999).status_code == 404
    assert client.get("/registrations/missing").status_code == 404


def test_capacity_atomic_under_concurrency(client, app):
    with app.state.factory.begin() as db:
        db.get(Event, 1).capacity = 3

    def submit(i):
        return post(client, key=f"parallel-{i}", email=f"user{i}@example.test").status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        codes = list(executor.map(submit, range(12)))
    assert codes.count(201) == 3
    assert codes.count(409) == 9
    with app.state.factory() as db:
        assert db.get(Event, 1).booked == 3
        assert len(list(db.scalars(select(Registration)))) == 3


def test_metrics_labels_and_correlation(client):
    r = client.get("/events", headers={"X-Request-ID": "valid-correlation"})
    assert r.headers["X-Request-ID"] == "valid-correlation"
    assert len(client.get("/events", headers={"X-Request-ID": "bad value"}).headers["X-Request-ID"]) == 32
    client.get("/registrations/private-user-id")
    metrics = client.get("/metrics").text
    assert "eventpulse_http_requests_total" in metrics
    assert "eventpulse_http_duration_seconds_bucket" in metrics
    assert "private-user-id" not in metrics
    assert "eventpulse_inflight 1.0" in metrics
    assert 'eventpulse_service_info{version="1.0.0"}' in metrics


def test_metric_count_and_latency_bucket(client, app):
    for _ in range(6):
        client.get("/events")
    data = client.get("/operations/summary").json()
    assert data["requests"] == 6
    assert data["availability"] == 1
    assert data["histogram"][-1]["count"] == 6
    assert app.state.telemetry.registry.get_sample_value("eventpulse_http_requests_total", {"method": "GET", "route": "/events", "status": "200"}) == 6


def test_no_traffic_unknown(client):
    s = client.get("/operations/summary").json()
    assert s["availability"] is None
    assert s["p95"] is None
    assert s["budget_remaining"] is None


def test_slo_math():
    samples = [{"status": 200, "duration": 0.1}] * 99 + [{"status": 500, "duration": 0.7}]
    result = calculate(samples, 100)
    assert result["availability"] == 0.99
    assert result["rps"] == 1
    assert result["budget_remaining"] == 0
    assert result["burn_rate"] == 1
    assert result["p95"] == 0.1
    assert result["latency_sli"] == 0.99
    assert percentile([], 0.95) is None


def test_fault_token_and_validation(client):
    assert client.post("/operations/faults", json={"kind": "http500"}).status_code == 403
    assert inject(client, "unknown").status_code == 422
    assert inject(client, "latency", delay_ms=4000).status_code == 422
    assert inject(client, "http500", duration_seconds=121).status_code == 422
    assert client.post("/operations/faults", json={"kind": "http500"}, headers={"X-Lab-Token": TOKEN, "Origin": "https://evil.test"}).status_code == 403


def test_faults_disabled_default(tmp_path, monkeypatch):
    monkeypatch.delenv("ENABLE_FAULTS", raising=False)
    app = create_app(f"sqlite:///{tmp_path}/off.db")
    with TestClient(app) as client:
        assert inject(client, "http500").status_code == 403


def test_faults_require_local_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="local"):
        create_app(fault_enabled=True)


def test_faults_require_token(monkeypatch):
    monkeypatch.delenv("FAULT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="FAULT_TOKEN"):
        create_app(fault_enabled=True)


@pytest.mark.parametrize("kind,status", [("http500", 500), ("database", 503), ("dependency", 504), ("warning", 200), ("latency", 200)])
def test_fault_and_recovery(client, kind, status):
    assert inject(client, kind, delay_ms=20).status_code == 200
    assert client.get("/events").status_code == status
    if kind == "database":
        assert client.get("/health/ready").status_code == 503
        assert client.get("/health/live").status_code == 200
    inject(client, "none")
    assert client.get("/events").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_fault_expiry(client):
    inject(client, "http500", duration_seconds=1)
    time.sleep(1.05)
    assert client.get("/events").status_code == 200


def test_incident_dedup_notes_resolution(client, app):
    now = time.time()
    for _ in range(5):
        app.state.telemetry.record("GET", "/events", 500, 0.01)
    app.state.evaluate()
    time.sleep(1.05)
    app.state.evaluate()
    app.state.evaluate()
    data = client.get("/operations/incidents").json()
    assert len(data) == 1
    assert data[0]["severity"] == "SEV2"
    assert data[0]["status"] == "firing"
    assert data[0]["start"] >= now
    response = client.patch("/operations/incidents/" + data[0]["id"], json={"notes": "Confirmed injected HTTP errors"}, headers={"X-Lab-Token": TOKEN})
    assert response.status_code == 200
    app.state.telemetry.samples.clear()
    app.state.evaluate()
    item = client.get("/operations/incidents").json()[0]
    assert item["end"] >= item["start"]
    assert item["status"] == "resolved"
    assert item["notes"] == "Confirmed injected HTTP errors"
    assert len(item["timeline"]) == 3


def test_noise_does_not_alert(client, app):
    inject(client, "warning")
    for _ in range(8):
        assert client.get("/events").status_code == 200
    app.state.evaluate()
    assert client.get("/operations/incidents").json() == []


def test_low_traffic_does_not_alert(client, app):
    app.state.telemetry.record("GET", "/events", 500, 1)
    app.state.evaluate()
    assert client.get("/operations/incidents").json() == []


def test_experiment_empty_export(client):
    assert client.get("/operations/experiments").json()["runs"] == []
    assert client.get("/operations/experiments?format=csv").headers["content-type"].startswith("text/csv")


def test_non_loopback_fault_denied(app):
    with TestClient(app, client=("192.0.2.10", 1234)) as remote:
        assert inject(remote, "http500").status_code == 403


def test_real_database_probe_failure(client, app, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def broken():
        raise OperationalError("SELECT 1", {}, Exception("synthetic unavailable database connection"))

    with monkeypatch.context() as patch:
        patch.setattr(app.state.engine, "connect", broken)
        assert client.get("/health/ready").status_code == 503
        assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_registration_failure_metrics_include_validation_and_fault(client, app):
    assert post(client, email="invalid").status_code == 422
    inject(client, "http500")
    assert post(client).status_code == 500
    assert app.state.telemetry.registry.get_sample_value("eventpulse_registrations_total", {"outcome": "failure"}) == 2


def test_latency_signal_severity_and_dedup(client, app):
    for _ in range(6):
        app.state.telemetry.record("GET", "/events", 200, 0.75)
    app.state.evaluate()
    time.sleep(1.05)
    app.state.evaluate()
    items = client.get("/operations/incidents").json()
    assert len(items) == 1
    assert items[0]["kind"] == "latency"
    assert items[0]["severity"] == "SEV3"
    assert items[0]["evidence"]["metric"] == 0.75


def test_window_expiration_and_overspent_budget():
    from app.telemetry import Telemetry

    telemetry = Telemetry(2)
    telemetry.record("CUSTOM_UNBOUNDED_METHOD", "/events", 500, 0.1)
    assert telemetry.summary()["budget_remaining"] == -99
    assert telemetry.summary(now=time.time() + 3)["availability"] is None
    assert telemetry.registry.get_sample_value("eventpulse_http_requests_total", {"method": "OTHER", "route": "/events", "status": "500"}) == 1
