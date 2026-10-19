import hashlib
import time
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.wireless_api import Guest

HEADERS = {"X-Wireless-Demo": "1"}
PREFIX = "/wireless-lab"


@pytest.fixture
def app(tmp_path):
    return create_app(f"sqlite:///{tmp_path}/wireless.db", fault_enabled=False)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def guest(c):
    response = c.post(PREFIX + "/guest", headers=HEADERS)
    assert response.status_code == 201
    return response


def run(c, scenario="E"):
    response = c.post(PREFIX + "/runs", json={"scenario_id": scenario}, headers=HEADERS)
    assert response.status_code == 201, response.text
    return response.json()


def test_session_auth_csrf_cookie_and_logout(client):
    assert client.get(PREFIX + "/aps").status_code == 401
    assert client.post(PREFIX + "/guest").status_code == 403
    assert client.post(PREFIX + "/guest", headers={**HEADERS, "Origin": "https://attacker.test"}).status_code == 403
    response = guest(client)
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    assert response.headers["cache-control"] == "no-store"
    assert len(client.get(PREFIX + "/aps").json()) == 3
    assert client.delete(PREFIX + "/session", headers=HEADERS).json()["deleted"]
    assert client.get(PREFIX + "/session").status_code == 401


def test_isolation_and_sanitized_reports(client, app):
    guest(client)
    result = run(client)
    identifier = result["id"]
    assert result["analysis"]["clients"][0]["classification"] == "dhcp_failed"
    assert client.get(PREFIX + "/runs/" + identifier).json()["id"] == identifier
    assert len(client.get(PREFIX + "/runs/" + identifier + "/events").json()) > 0
    assert "timestamp_us,client" in client.get(PREFIX + "/runs/" + identifier + "/export?format=csv").text
    assert client.get(PREFIX + "/runs/" + identifier + "/export?format=exe").status_code == 422
    with TestClient(app) as other:
        guest(other)
        assert other.get(PREFIX + "/runs/" + identifier).status_code == 404
        assert other.get(PREFIX + "/runs/" + identifier + "/export").status_code == 404
        assert other.get(PREFIX + "/runs").json() == []
        other.post(PREFIX + "/aps", headers=HEADERS, json={"name": "New AP", "ssid": "Guest", "channel": 11})
        assert len(other.get(PREFIX + "/aps").json()) == 4
    assert len(client.get(PREFIX + "/aps").json()) == 3
    assert client.get("/events").status_code == 200
    metrics = client.get("/metrics").text
    assert 'wirelesslab_runs_total{scenario="E",verdict="pass"} 1.0' in metrics
    assert identifier not in metrics


@pytest.mark.parametrize("payload", [{"scenario_id": "../../etc/passwd"}, {"scenario_id": "A", "command": "id"}, {"scenario_id": "Z"}])
def test_typed_input(client, payload):
    guest(client)
    assert client.post(PREFIX + "/runs", headers=HEADERS, json=payload).status_code == 422


def test_no_guest_upload_or_capture_commands(client):
    guest(client)
    assert client.post(PREFIX + "/uploads", headers=HEADERS, content=b"not a pcap").status_code == 403
    assert client.get(PREFIX + "/fixtures/E/capture").status_code == 404
    assert client.get(PREFIX + "/fixtures/A/capture").content[:4] == b"\xd4\xc3\xb2\xa1"
    assert client.post(PREFIX + "/capture", headers=HEADERS).status_code == 404
    assert not client.get(PREFIX + "/capabilities").json()["live_capture"]


def test_quota_and_expired_session(client, app):
    guest(client)
    token = client.cookies.get("wl_guest")
    identifier = hashlib.sha256(token.encode()).hexdigest()
    with app.state.factory.begin() as db:
        db.get(Guest, identifier).quota_count = 12
    assert client.post(PREFIX + "/runs", headers=HEADERS, json={"scenario_id": "H"}).status_code == 429
    with app.state.factory.begin() as db:
        item = db.get(Guest, identifier)
        item.quota_start = time.time() - 61
    assert run(client, "H")["verdict"] == "pass"
    with app.state.factory.begin() as db:
        db.get(Guest, identifier).expires = time.time() - 1
    assert client.get(PREFIX + "/runs").status_code == 401


def test_ap_bounds_and_capability_input(client):
    guest(client)
    assert client.post(PREFIX + "/aps", headers=HEADERS, json={"name": "<script>", "ssid": "s", "channel": 1}).status_code == 422
    assert client.post(PREFIX + "/aps", headers=HEADERS, json={"name": "ap", "ssid": "s", "channel": 166}).status_code == 422
    for i in range(5):
        assert client.post(PREFIX + "/aps", headers=HEADERS, json={"name": f"AP {i}", "ssid": "s", "channel": 1}).status_code == 201
    assert client.post(PREFIX + "/aps", headers=HEADERS, json={"name": "overflow", "ssid": "s", "channel": 1}).status_code == 409
