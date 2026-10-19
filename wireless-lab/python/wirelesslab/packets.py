"""Bounded TShark -r ingestion. No -i, live capture, keys, decrypt or shell commands."""

import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
from functools import lru_cache
import os
from pathlib import Path
import secrets
import re
import shutil
import subprocess
import tempfile
import time
from .schema import WirelessEvent

MAX_BYTES = 1_048_576
MAX_PACKETS = 5000
FIELDS = [
    "frame.number",
    "frame.time_epoch",
    "wlan.fc.type_subtype",
    "wlan.sa",
    "wlan.da",
    "wlan.ta",
    "wlan.ra",
    "dhcp.hw.mac_addr",
    "wlan.bssid",
    "wlan.ssid",
    "wlan.fixed.status_code",
    "wlan.fixed.reason_code",
    "wlan.fixed.auth.alg",
    "wlan.fixed.auth_seq",
    "wlan.seq",
    "eth.src",
    "eth.dst",
    "eapol.type",
    "wlan_rsna_eapol.keydes.msgnr",
    "dhcp.option.dhcp",
    "dns.flags.response",
    "dns.flags.rcode",
]
MAGICS = {
    b"\xd4\xc3\xb2\xa1",
    b"\xa1\xb2\xc3\xd4",
    b"\x4d\x3c\xb2\xa1",
    b"\xa1\xb2\x3c\x4d",
    b"\x0a\x0d\x0d\x0a",
}


class CaptureUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def available_fields():
    executable = shutil.which("tshark")
    if not executable:
        raise CaptureUnavailable(
            "TShark is not installed; JSON-event scenarios remain available"
        )
    result = subprocess.run(
        [executable, "-G", "fields"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    if result.returncode:
        raise CaptureUnavailable("Cannot query TShark field support")
    fields = {
        line.split("\t")[2]
        for line in result.stdout.splitlines()
        if line.startswith("F\t") and len(line.split("\t")) > 2
    }
    selected = [f for f in FIELDS if f in fields]
    if "frame.time_epoch" not in selected:
        raise CaptureUnavailable("Required TShark timestamp field is unavailable")
    return executable, selected


def _int(value, default=-1):
    try:
        return int(value, 16) if value.lower().startswith("0x") else int(value)
    except (ValueError, AttributeError):
        return default


def normalize_rows(rows, pseudonymize=True):
    events = []
    salt = secrets.token_bytes(16)

    def identity(value, prefix):
        if not value:
            return "unknown_" + prefix
        if value.lower() == "ff:ff:ff:ff:ff:ff":
            return "broadcast"
        return (
            prefix
            + "_"
            + hashlib.sha256(salt + value.lower().encode()).hexdigest()[:12]
            if pseudonymize
            else value.lower()
        )

    for row in rows:
        subtype = _int(row.get("wlan.fc.type_subtype", ""))
        origin_ap = row.get("wlan.bssid", "")
        source = row.get("wlan.sa") or row.get("eth.src", "")
        destination = row.get("wlan.da") or row.get("eth.dst", "")
        direction = (
            "ap_to_client"
            if origin_ap and source == origin_ap
            else "client_to_ap"
            if origin_ap and destination == origin_ap
            else "unknown"
        )
        # Transmitter/receiver identify the wireless station even when SA/DA are wired hosts.
        transmitter, receiver = row.get("wlan.ta"), row.get("wlan.ra")
        if origin_ap and transmitter == origin_ap:
            direction = "ap_to_client"
        elif origin_ap and receiver == origin_ap:
            direction = "client_to_ap"
        # WLAN addressing identifies the AP via BSSID. Ethernet EAPOL does not provide this context.
        client = (
            (receiver or destination)
            if direction == "ap_to_client"
            else (transmitter or source)
        )
        code = _int(row.get("wlan.fixed.status_code", ""))
        kind = {
            0: "assoc_request",
            1: "assoc_ok" if code == 0 else "assoc_reject",
            4: "probe_request",
            5: "probe_response",
            8: "beacon",
            10: "disassoc",
            12: "deauth",
        }.get(subtype)
        algorithm = _int(row.get("wlan.fixed.auth.alg", ""))
        auth_sequence = _int(row.get("wlan.fixed.auth_seq", ""))
        if subtype == 11:
            if code > 0:
                kind = "auth_fail"
            elif algorithm == 3 and auth_sequence in (1, 2):
                kind = "sae_commit" if auth_sequence == 1 else "sae_confirm"
            elif auth_sequence == 1:
                kind = "auth_request"
            elif auth_sequence == 2 and code == 0:
                kind = "auth_ok"
        message = _int(row.get("wlan_rsna_eapol.keydes.msgnr", ""))
        if message in (1, 2, 3, 4):
            kind = f"eapol_{message}"
        dhcp = _int(row.get("dhcp.option.dhcp", ""))
        if dhcp in (1, 2, 3, 5, 6):
            client = row.get("dhcp.hw.mac_addr") or client
            kind = {
                1: "dhcp_discover",
                2: "dhcp_offer",
                3: "dhcp_request",
                5: "dhcp_ack",
                6: "dhcp_fail",
            }[dhcp]
        if row.get("dns.flags.response") in ("1", "True"):
            kind = (
                "dns_ok" if _int(row.get("dns.flags.rcode", ""), 0) == 0 else "dns_fail"
            )
        elif row.get("dns.flags.response") in ("0", "False"):
            kind = "dns_query"
        if kind is None and 0x20 <= subtype <= 0x2F:
            kind = "data"
        if kind is None:
            continue
        if kind in ("assoc_ok", "assoc_reject") and code < 0:
            continue  # A missing status is not an explicit rejection or success.
        if kind in ("deauth", "disassoc"):
            code = _int(row.get("wlan.fixed.reason_code", ""))
        try:
            timestamp = str(row["frame.time_epoch"])
            micros = int(Decimal(timestamp) * 1_000_000)
        except (KeyError, InvalidOperation, ValueError, OverflowError) as exc:
            raise ValueError("Capture contains an invalid timestamp") from exc
        missing = [
            key for key in ("wlan.bssid", "wlan.sa", "wlan.da") if not row.get(key)
        ]
        ssid = row.get("wlan.ssid")
        if ssid and pseudonymize:
            ssid = "ssid_" + hashlib.sha256(salt + ssid.encode()).hexdigest()[:12]
        if len(ssid or "") > 64:
            ssid = (ssid or "")[:64]
        event = WirelessEvent(
            event_id="frame_" + str(_int(row.get("frame.number", ""), len(events) + 1)),
            timestamp_us=micros,
            capture_timestamp=timestamp,
            client=identity(client, "client"),
            ap=identity(origin_ap, "ap"),
            kind=kind,
            code=code,
            sequence=_int(row.get("wlan.seq", "")),
            origin="packet",
            direction=direction,
            ssid=ssid,
            frame_subtype=f"0x{subtype:02x}" if subtype >= 0 else None,
            link_layer="ieee80211" if subtype >= 0 else "ethernet",
            missing_fields=missing,
        )
        events.append(event.model_dump())
    return events


def parse_capture(data: bytes, filename="capture.pcap", pseudonymize=True):
    if not re.fullmatch(
        r"[A-Za-z0-9_.-]{1,100}\.(pcap|pcapng)", filename, re.IGNORECASE
    ):
        raise ValueError("Use a plain .pcap or .pcapng file name, never a path")
    if (
        not isinstance(data, bytes)
        or len(data) > MAX_BYTES
        or len(data) < 24
        or data[:4] not in MAGICS
    ):
        raise ValueError("Malformed, unsupported or oversized capture; maximum 1 MiB")
    executable, selected = available_fields()
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="wirelesslab-pcap-") as temporary:
        capture = Path(temporary) / "input.pcap"
        capture.write_bytes(data)
        command = [
            executable,
            "-n",
            "-r",
            str(capture),
            "-c",
            str(MAX_PACKETS + 1),
            "-o",
            "wlan.enable_decryption:FALSE",
            "-T",
            "fields",
            "-E",
            "separator=\t",
            "-E",
            "quote=d",
            "-E",
            "occurrence=f",
        ]
        for field in selected:
            command.extend(["-e", field])
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
                shell=False,
                env={**os.environ, "WIRESHARK_CONFIG_DIR": temporary},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CaptureUnavailable(
                "Bounded TShark execution failed or timed out"
            ) from exc
        if process.returncode or len(process.stdout) > 4_000_000:
            raise ValueError(
                "TShark rejected the capture or extraction limit was exceeded"
            )
        rows = list(
            csv.DictReader(
                io.StringIO(process.stdout),
                fieldnames=selected,
                delimiter="\t",
                quotechar='"',
            )
        )
        if len(rows) > MAX_PACKETS:
            raise ValueError("Capture exceeds 5000-packet limit")
        events = normalize_rows(rows, pseudonymize)
    if not events:
        raise ValueError("No supported wireless/EAPOL/DHCP/DNS evidence in capture")
    return {
        "events": events,
        "packet_count": len(rows),
        "supported_events": len(events),
        "parsing_duration_ms": (time.perf_counter() - start) * 1000,
        "missing_extractor_fields": [f for f in FIELDS if f not in selected],
        "limitations": [
            "File-only offline extraction; no live capture or decryption.",
            "Missing packets/fields are unknown, not evidence of a cause.",
            "Ethernet EAPOL is not complete IEEE 802.11 association evidence.",
            "EAPOL and SAE observations do not verify cryptographic correctness.",
        ],
    }
