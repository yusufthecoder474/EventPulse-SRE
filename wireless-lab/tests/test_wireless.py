import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from wirelesslab.analyze import analyze_events, AnalyzerUnavailable  # noqa: E402
from wirelesslab.packets import parse_capture, normalize_rows, CaptureUnavailable  # noqa: E402
from wirelesslab.scenarios import definitions, run_scenario, approved_capture  # noqa: E402
from wirelesslab.schema import WirelessEvent  # noqa: E402


@pytest.mark.parametrize("definition", definitions(), ids=lambda d: d["id"])
def test_scenario(definition):
    result = run_scenario(definition["id"])
    assert result["verdict"] == "pass"
    assert result["actual_classifications"] == definition["expected_classifications"]
    assert all(result["assertions"].values())
    assert result["analysis"]["input_events"] == len(result["events"])


def test_radio_eapol_and_ethernet_are_distinct():
    radio = run_scenario("A")
    assert {e["kind"] for e in radio["events"]} >= {
        "beacon",
        "probe_request",
        "probe_response",
        "auth_ok",
        "assoc_ok",
        "eapol_4",
    }
    assert radio["analysis"]["clients"][0]["classification"] == "association_success"
    data = parse_capture(
        (ROOT / "fixtures/ethernet-eapol.pcap").read_bytes(), "ethernet.pcap"
    )
    assert all(
        e["link_layer"] == "ethernet" and e["ap"] == "unknown_ap"
        for e in data["events"]
    )
    analysis = analyze_events(data["events"])
    assert all(c["classification"] == "incomplete" for c in analysis["clients"])


def test_sae_fixture_is_separate_from_key_establishment():
    events = json.loads((ROOT / "fixtures/wpa3-sae-events.json").read_text())
    result = analyze_events(events)
    client = result["clients"][0]
    assert client["classification"] == "association_success"
    assert "sae_commit" in {e["kind"] for e in events}
    assert client["eapol_messages_observed"] == []


@pytest.mark.parametrize(
    "filename,data",
    [
        ("bad.txt", b"x" * 30),
        ("../x.pcap", b"x" * 30),
        ("x.pcap", b"x" * 30),
        ("x.pcap", b"\xd4\xc3\xb2\xa1" + b"x" * 1048576),
    ],
    ids=["extension", "path", "magic", "size"],
)
def test_reject_capture_before_subprocess(filename, data, monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail("Invalid input reached a subprocess")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ValueError):
        parse_capture(data, filename)


def test_privacy_and_timestamp_preservation():
    data = (ROOT / "fixtures/association-success.pcap").read_bytes()
    output = parse_capture(data, "sample.pcap")
    serialized = json.dumps(output)
    assert "02:00:00:00:01:01" not in serialized
    assert "EventPulse-Lab" not in serialized
    event = output["events"][0]
    assert event["timestamp_us"] == 1700000000000000
    assert event["capture_timestamp"].startswith("1700000000.")
    assert not any(
        k in serialized for k in ["wlan_rsna_eapol.keydes.key_data", "dns.qry.name"]
    )


def test_missing_status_is_unknown():
    row = {
        "frame.number": "1",
        "frame.time_epoch": "1.000001",
        "wlan.fc.type_subtype": "1",
        "wlan.bssid": "02:00:00:00:00:01",
    }
    assert normalize_rows([row]) == []


def test_wireless_transmitter_identity():
    row = {
        "frame.number": "1",
        "frame.time_epoch": "1",
        "wlan.fc.type_subtype": "0x20",
        "wlan.bssid": "02:00:00:00:00:01",
        "wlan.sa": "02:00:00:00:99:99",
        "wlan.da": "02:00:00:00:00:02",
        "wlan.ta": "02:00:00:00:00:01",
        "wlan.ra": "02:00:00:00:00:02",
    }
    event = normalize_rows([row], False)[0]
    assert event["client"] == row["wlan.ra"]
    assert event["direction"] == "ap_to_client"


def test_safe_file_subprocess_and_timeout(monkeypatch):
    from wirelesslab import packets

    monkeypatch.setattr(
        packets, "available_fields", lambda: ("/usr/bin/tshark", ["frame.time_epoch"])
    )

    def bounded(command, **kwargs):
        assert "-r" in command and "-i" not in command
        assert kwargs["shell"] is False and kwargs["timeout"] == 12
        assert "wlan.enable_decryption:FALSE" in command
        raise subprocess.TimeoutExpired(command, 12)

    monkeypatch.setattr(subprocess, "run", bounded)
    with pytest.raises(CaptureUnavailable):
        parse_capture(
            (ROOT / "fixtures/association-success.pcap").read_bytes(), "sample.pcap"
        )


@pytest.mark.parametrize(
    "patch",
    [
        {"client": "bad\tcommand"},
        {"timestamp_us": -1},
        {"kind": "shell"},
        {"kind": "auth_ok", "code": 13},
    ],
)
def test_schema_validation(patch):
    event = dict(
        event_id="one", timestamp_us=1, client="c", ap="a", kind="auth_ok", code=0
    )
    with pytest.raises(ValidationError):
        WirelessEvent.model_validate({**event, **patch})


def test_no_arbitrary_scenario_path():
    with pytest.raises(ValueError):
        run_scenario("../../etc/passwd")
    with pytest.raises(ValueError):
        approved_capture("E")


def test_bounded_analyzer_and_unavailable(monkeypatch):
    with pytest.raises(ValueError):
        analyze_events([{}] * 50001)
    monkeypatch.setenv("WIRELESS_ANALYZER", "/nonexistent/wireless-analyzer")
    with pytest.raises(AnalyzerUnavailable):
        analyze_events([])
