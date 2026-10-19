import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

P = "/wireless-lab"
H = {"X-Wireless-Demo": "1"}
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def app(tmp_path):
    return create_app(f"sqlite:///{tmp_path}/test-v3.db", fault_enabled=False)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        assert c.post(P + "/guest", headers=H).status_code == 201
        yield c


def test_import_requires_session_consent_and_isolation(client, app):
    payload = (ROOT / "wireless-lab/fixtures/v3/ethernet-eapol.pcapng").read_bytes()
    assert client.post(P + "/imports", headers=H, content=payload).status_code == 403
    headers = {**H, "X-Lab-Authorized": "true", "X-File-Name": "capture.pcapng"}
    result = client.post(P + "/imports", headers=headers, content=payload)
    assert result.status_code == 201, result.text
    data = result.json()
    assert data["extraction"]["format"] == "pcapng"
    assert data["handshakes"]["sessions"][0]["classification"] == "HANDSHAKE_COMPLETE"
    assert data["verdict"] == "analysis_only"
    exported = client.get(P + "/runs/" + data["id"] + "/export").text
    assert "02:00:00:00:10:01" not in exported and "wlan_rsna_eapol.keydes.key_data" not in exported
    with TestClient(app) as other:
        assert other.post(P + "/imports", headers=headers, content=payload).status_code == 401
        other.post(P + "/guest", headers=H)
        assert other.get(P + "/runs/" + data["id"]).status_code == 404
    assert client.post(P + "/uploads", headers=H, content=payload).status_code == 403
    assert client.delete(P + "/session", headers=H).json()["deleted"]
    assert client.get(P + "/runs/" + data["id"]).status_code == 401


@pytest.mark.parametrize(
    "name,data,code",
    [("../capture.pcap", b"x" * 30, 422), ("x.pcap", b"x" * 30, 422), ("x.pcap", b"x" * 1048577, 413)],
    ids=["path", "magic", "size"],
)
def test_import_validation(client, name, data, code):
    r = client.post(P + "/imports", headers={**H, "X-Lab-Authorized": "true", "X-File-Name": name}, content=data)
    assert r.status_code == code
    assert client.get(P + "/runs").json() == []


def test_test_plan_suite_and_export(client, app):
    assert len(client.get(P + "/plans").json()["cases"]) == 24
    r = client.post(P + "/validations", headers=H, json={})
    assert r.status_code == 201, r.text
    data = r.json()
    report = data["validation"]
    assert (report["unique_scenarios"], report["executed_runs"], report["passed_runs"], report["validation_failures"]) == (24, 24, 24, 0)
    assert client.get(P + "/runs/" + data["id"] + "/validation-export").json() == report
    csv = client.get(P + "/runs/" + data["id"] + "/validation-export?format=csv")
    assert "P01" in csv.text and "expected_behavior" in csv.text
    with TestClient(app) as other:
        other.post(P + "/guest", headers=H)
        assert other.get(P + "/runs/" + data["id"] + "/validation-export").status_code == 404
    assert client.post(P + "/validations", headers=H, json={"test_id": "P99"}).status_code == 422
    assert client.post(P + "/validations", headers=H, json={"test_id": "../../etc/passwd"}).status_code == 422
    assert len(client.get(P + "/runs").json()) == 1
    assert json.loads(client.get(P + "/runs/" + data["id"] + "/export").text)["validation"]["passed_runs"] == 24


def test_import_quota(client, app):
    import hashlib
    from app.wireless_api import Guest

    owner = hashlib.sha256(client.cookies.get("wl_guest").encode()).hexdigest()
    with app.state.factory.begin() as db:
        db.get(Guest, owner).quota_count = 12
    assert client.post(P + "/imports", headers={**H, "X-Lab-Authorized": "true"}, content=b"x" * 30).status_code == 429
