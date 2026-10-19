import json
from pathlib import Path
import struct
import sys
import subprocess
import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from wirelesslab.capture_format import inspect_container, WARNING  # noqa: E402
from wirelesslab.validation import plans, execute_case, import_capture  # noqa: E402
from wirelesslab.analyze import analyze_handshakes  # noqa: E402
from wirelesslab.schema import WirelessEvent  # noqa: E402


@pytest.mark.parametrize("case", plans()["cases"], ids=lambda c: c["id"])
def test_registered_plan(case):
    row = execute_case(case["id"])
    assert row["verdict"] == "pass"
    assert row["observed_behavior"] == case["expected"]
    assert row["event_references"] and row["execution_duration_ms"] > 0
    assert row["evidence_origin"] == "synthetic"


@pytest.mark.parametrize(
    "name,format,packets",
    [
        ("ethernet-4.pcap", "pcap", 4),
        ("ethernet-eapol.pcapng", "pcapng", 4),
        ("ethernet-ip-only.pcap", "pcap", 1),
    ],
)
def test_container_and_import(name, format, packets):
    data = (ROOT / "fixtures/v3" / name).read_bytes()
    meta = inspect_container(data)
    assert meta["format"] == format and meta["packet_count"] == packets
    result = import_capture(data, name)
    assert WARNING in result["extraction"]["warnings"]
    assert not result["extraction"]["management_evidence_available"]
    assert not result["extraction"]["real_capture_validated"]
    assert result["extraction"]["origin"] == "synthetic_generated"
    assert all(
        c["classification"] == "incomplete" for c in result["analysis"]["clients"]
    )
    if "ip-only" not in name:
        assert result["actual_classifications"] == ["incomplete"]
        assert (
            result["handshakes"]["sessions"][0]["classification"]
            == "HANDSHAKE_COMPLETE"
        )
        assert all(
            x not in json.dumps(result)
            for x in ["02:00:00:00:01:01", "02:00:00:00:10:01"]
        )
    else:
        assert result["events"] == []


@pytest.mark.parametrize(
    "variant",
    [
        "truncated_header",
        "truncated_payload",
        "bad_link",
        "bad_length",
        "bad_version",
        "bad_subsecond",
        "over_packets",
        "ng_truncated",
        "ng_trailer",
        "ng_unknown_interface",
        "ng_secret",
    ],
)
def test_malformed_containers(variant):
    pcap = (ROOT / "fixtures/v3/ethernet-4.pcap").read_bytes()
    ng = (ROOT / "fixtures/v3/ethernet-eapol.pcapng").read_bytes()
    if variant == "truncated_header":
        data = pcap[:30]
    elif variant == "truncated_payload":
        data = pcap[:-1]
    elif variant == "bad_link":
        data = pcap[:20] + struct.pack("<I", 101) + pcap[24:]
    elif variant == "bad_length":
        data = pcap[:32] + struct.pack("<I", 999999) + pcap[36:]
    elif variant == "bad_version":
        data = pcap[:4] + b"\x03\x00" + pcap[6:]
    elif variant == "bad_subsecond":
        data = pcap[:28] + struct.pack("<I", 1000000) + pcap[32:]
    elif variant == "over_packets":
        data = pcap[:24] + (pcap[24:]) * 1251
    elif variant == "ng_truncated":
        data = ng[:-1]
    elif variant == "ng_trailer":
        data = ng[:-4] + struct.pack("<I", 12)
    elif variant == "ng_unknown_interface":
        data = ng[:56] + struct.pack("<I", 100) + ng[60:]
    else:
        data = ng + struct.pack("<IIII", 10, 16, 0, 16)
    with pytest.raises(ValueError):
        inspect_container(data)


@pytest.mark.parametrize("suffix,caplen", [(b"\x01", 1), (b"", 0)])
def test_pcap_boundary_empty_and_nano(suffix, caplen):
    header = struct.pack("<IHHIIII", 0xA1B23C4D, 2, 4, 0, 0, 65535, 1)
    raw = header + (
        struct.pack("<IIII", 1, 123456789, caplen, caplen) + suffix if suffix else b""
    )
    meta = inspect_container(raw)
    assert meta["packet_count"] == (1 if suffix else 0)
    if suffix:
        assert meta["first_timestamp"] == "1.123456789"


def test_schema_counter_bounds_and_command_safe(monkeypatch):
    event = json.loads((ROOT / "fixtures/v3/handshake-complete.json").read_text())[0]
    with pytest.raises(ValidationError):
        WirelessEvent.model_validate({**event, "replay_counter": str(2**64)})
    with pytest.raises(ValueError):
        analyze_handshakes([event], observed_until_us=-1)

    def fail(command, **kw):
        assert "--handshakes" in command and kw["shell"] is False and kw["timeout"] == 8
        assert "input" in kw
        raise subprocess.TimeoutExpired(command, 8)

    monkeypatch.setattr(subprocess, "run", fail)
    from wirelesslab.analyze import AnalyzerUnavailable

    with pytest.raises(AnalyzerUnavailable):
        analyze_handshakes([event])


def test_raw_80211_and_zero_placeholder_flags():
    result = import_capture(
        (ROOT / "fixtures/association-success.pcap").read_bytes(), "a.pcap"
    )
    assert result["extraction"]["management_evidence_available"]
    assert result["handshakes"]["sessions"][0]["classification"] == "HANDSHAKE_COMPLETE"
    assert not result["handshakes"]["cryptographically_verified"]
    assert [
        p["message"] for p in result["handshakes"]["sessions"][0]["packet_references"]
    ] == [1, 2, 3, 4]


def test_unknown_plan_is_not_a_path():
    with pytest.raises(ValueError):
        execute_case("../../etc/passwd")
