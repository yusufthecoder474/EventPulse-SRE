"""Generate small synthetic PCAPs. Never sniffs, transmits or reads an interface."""

import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
AP = "02:00:00:00:01:01"
CLIENT = "02:00:00:00:10:01"
BASE = 1700000000000000


def mac(value):
    return bytes.fromhex(value.replace(":", ""))


def ssid():
    return bytes([0, 13]) + b"EventPulse-Lab"


def body_auth(algo=0, seqnum=1, status=0):
    return struct.pack("<HHH", algo, seqnum, status)


def body_assoc(status=0):
    return struct.pack("<HHH", 0x11, status, 0xC001)


def frame(subtype, body, from_ap=False, t=0):
    header = (
        struct.pack("<HH", subtype << 4, 0)
        + mac(CLIENT if from_ap else AP)
        + mac(AP if from_ap else CLIENT)
        + mac(AP)
        + struct.pack("<H", (t // 1000 % 4096) << 4)
    )
    return t, b"\0\0\x08\0\0\0\0\0" + header + body


def connection(status=0, delay=100000):
    return [
        frame(11, body_auth(seqnum=1), t=100000),
        frame(11, body_auth(seqnum=2), True, t=200000),
        frame(0, struct.pack("<HH", 0x11, 10) + ssid(), t=300000),
        frame(1, body_assoc(status), True, t=300000 + delay),
    ]


def key(message, ethernet=False):
    from_ap = message in (1, 3)
    key_info = {1: 0x008A, 2: 0x010A, 3: 0x03CA, 4: 0x030A}[message]
    descriptor = (
        bytes([2])
        + struct.pack("!HHQ", key_info, 16, 1 if message < 3 else 2)
        + bytes(32 + 16 + 8 + 8 + 16)
        + struct.pack("!H", 0)
    )
    payload = struct.pack("!BBH", 2, 3, len(descriptor)) + descriptor
    if ethernet:
        packet = (
            mac(CLIENT if from_ap else AP)
            + mac(AP if from_ap else CLIENT)
            + struct.pack("!H", 0x888E)
            + payload
        )
    else:
        header = (
            struct.pack("<HH", 0x0208 if from_ap else 0x0108, 0)
            + mac(CLIENT if from_ap else AP)
            + mac(AP if from_ap else CLIENT)
            + mac(AP)
            + struct.pack("<H", message << 4)
        )
        packet = (
            b"\0\0\x08\0\0\0\0\0" + header + b"\xaa\xaa\x03\0\0\0\x88\x8e" + payload
        )
    return 500000 + message * 100000, packet


def write_pcap(path, packets, link_type=127):
    data = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, link_type)
    for offset, packet in packets:
        timestamp = BASE + offset
        data += (
            struct.pack(
                "<IIII",
                timestamp // 1000000,
                timestamp % 1000000,
                len(packet),
                len(packet),
            )
            + packet
        )
    path.write_bytes(data)


def event(kind, offset, **kw):
    return {
        "event_id": f"e_{kind}_{offset}",
        "timestamp_us": BASE + offset,
        "client": CLIENT,
        "ap": AP,
        "kind": kind,
        "code": -1,
        "sequence": 1,
        "origin": "synthetic",
        "direction": "unknown",
        "reported_state": "unknown",
        **kw,
    }


def synthetic_connection():
    return [
        event("auth_request", 100000),
        event("auth_ok", 200000, code=0),
        event("assoc_request", 300000),
        event("assoc_ok", 400000, code=0),
    ]


def main():
    fixtures = ROOT / "fixtures"
    fixtures.mkdir(exist_ok=True)
    beacon_body = struct.pack("<QHH", 0, 100, 0x11) + ssid() + bytes([3, 1, 6])
    beacon = frame(8, beacon_body, True, t=0)
    # Discovery identifiers use the broadcast address and are not client associations.
    raw = beacon[1]
    beacon = (0, raw[:12] + mac("ff:ff:ff:ff:ff:ff") + raw[18:])
    probe = frame(4, ssid(), t=10000)
    response = frame(5, beacon_body, True, t=20000)
    write_pcap(
        fixtures / "association-success.pcap",
        [beacon, probe, response, *connection(), *[key(n) for n in range(1, 5)]],
    )
    write_pcap(fixtures / "association-rejected.pcap", connection(status=17))
    write_pcap(
        fixtures / "authentication-failed.pcap",
        [
            frame(11, body_auth(seqnum=1), t=100000),
            frame(11, body_auth(seqnum=2, status=13), True, t=200000),
        ],
    )
    write_pcap(
        fixtures / "client-disconnected.pcap",
        [*connection(), frame(12, struct.pack("<H", 3), True, t=900000)],
    )
    write_pcap(fixtures / "association-delayed.pcap", connection(delay=1500000))
    write_pcap(
        fixtures / "ethernet-eapol.pcap",
        [key(n, True) for n in range(1, 5)],
        link_type=1,
    )
    # These are explicit, labeled management/IP-layer simulations, never fictional PCAPs.
    events = {
        "dhcp-failed.json": [
            *synthetic_connection(),
            event("dhcp_discover", 500000),
            event("dhcp_fail", 3500000),
        ],
        "dns-failed.json": [
            *synthetic_connection(),
            event("dhcp_ack", 600000),
            event("dns_query", 700000),
            event("dns_fail", 800000, code=3),
        ],
        "reordered-duplicate.json": [],
        "incomplete.json": [event("assoc_request", 300000)],
        "controller-inconsistent.json": [
            *synthetic_connection(),
            event(
                "controller_update",
                8000000,
                origin="controller",
                reported_state="disconnected",
            ),
        ],
        "wpa3-sae-events.json": [],
    }
    ordered = synthetic_connection()
    events["reordered-duplicate.json"] = [
        ordered[2],
        ordered[0],
        ordered[1],
        ordered[2],
        ordered[3],
    ]
    sae = [
        event("sae_commit", 100000, direction="client_to_ap"),
        event("sae_commit", 200000, direction="ap_to_client"),
        event("sae_confirm", 300000, direction="client_to_ap"),
        event("sae_confirm", 400000, direction="ap_to_client"),
        event("assoc_request", 500000),
        event("assoc_ok", 600000, code=0),
    ]
    events["wpa3-sae-events.json"] = sae
    for name, data in events.items():
        (fixtures / name).write_text(json.dumps(data, indent=2) + "\n")
    specs = [
        (
            "A",
            "Successful association",
            "association-success.pcap",
            "association_success",
            "generated_pcap",
        ),
        (
            "B",
            "AP association rejection",
            "association-rejected.pcap",
            "association_rejected",
            "generated_pcap",
        ),
        (
            "C",
            "Authentication rejection",
            "authentication-failed.pcap",
            "authentication_failed",
            "generated_pcap",
        ),
        (
            "D",
            "Client disconnected",
            "client-disconnected.pcap",
            "disconnected",
            "generated_pcap",
        ),
        (
            "E",
            "DHCP allocation failure",
            "dhcp-failed.json",
            "dhcp_failed",
            "synthetic_events",
        ),
        (
            "F",
            "DNS failure after IP configuration",
            "dns-failed.json",
            "dns_failed",
            "synthetic_events",
        ),
        (
            "G",
            "Delayed association",
            "association-delayed.pcap",
            "association_delayed",
            "generated_pcap",
        ),
        (
            "H",
            "Duplicate and out-of-order events",
            "reordered-duplicate.json",
            "association_success",
            "synthetic_events",
        ),
        (
            "I",
            "Missing connection evidence",
            "incomplete.json",
            "incomplete",
            "synthetic_events",
        ),
        (
            "J",
            "Delayed inconsistent controller update",
            "controller-inconsistent.json",
            "management_inconsistent",
            "synthetic_events",
        ),
    ]
    catalog = []
    for ident, title, filename, expected, evidence in specs:
        catalog.append(
            {
                "id": ident,
                "title": title,
                "objective": f"Validate {title.lower()} without inferring an unobserved cause.",
                "preconditions": ["Offline local lab", "Compiled C++17 analyzer"]
                + (["TShark installed"] if evidence == "generated_pcap" else []),
                "fixture": filename,
                "evidence_type": evidence,
                "origin": "Generated synthetic laboratory data; no hardware or real users",
                "expected_classifications": [expected],
                "min_duplicates": 1 if ident == "H" else 0,
                "min_out_of_order": 1 if ident == "H" else 0,
                "reproduction": f"python wireless-lab/scripts/run_scenarios.py --scenario {ident}",
            }
        )
    (ROOT / "scenarios/catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(
        "Generated six synthetic packet captures, six event fixtures and ten scenario definitions."
    )


if __name__ == "__main__":
    main()
