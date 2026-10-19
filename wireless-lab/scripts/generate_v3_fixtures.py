from pathlib import Path
import json
import runpy
import struct
import hashlib

r = Path(__file__).resolve().parents[2]
f = r / "wireless-lab/fixtures/v3"
f.mkdir(exist_ok=True)


def hs(message, offset, client="clientA", counter=None):
    return dict(
        event_id=f"{client}_m{message}_{offset}",
        timestamp_us=1700000000000000 + offset,
        client=client,
        ap="apA",
        authenticator="apA",
        kind=f"eapol_{message}",
        origin="synthetic",
        direction="ap_to_client" if message in [1, 3] else "client_to_ap",
        replay_counter=str(
            counter if counter is not None else 10 if message < 3 else 11
        ),
        key_info={1: 138, 2: 266, 3: 970, 4: 778}[message],
        descriptor_type=2,
    )


base = [hs(i, i * 100000) for i in range(1, 5)]
fixtures = {
    "complete": base,
    "missing_m1": base[1:],
    "missing_m2": [base[i] for i in [0, 2, 3]],
    "missing_m3": [base[i] for i in [0, 1, 3]],
    "missing_m4": base[:3],
    "reordered": [hs(1, 100000), hs(3, 200000), hs(2, 300000), hs(4, 400000)],
    "retransmitted": [base[0], hs(1, 150000), *base[1:]],
    "timeout": base[:2]
    + [
        dict(
            event_id="tail",
            timestamp_us=1700000007000000,
            client="clientA",
            ap="apA",
            kind="data",
            origin="synthetic",
        )
    ],
    "insufficient": [
        {
            k: v
            for k, v in base[0].items()
            if k not in ["replay_counter", "key_info", "descriptor_type"]
        }
    ],
    "concurrent": base
    + [
        hs(i, i * 100000 + 50000, "clientB", counter=20 if i < 3 else 25)
        for i in range(1, 5)
    ],
}
expected = [
    "HANDSHAKE_COMPLETE",
    *["HANDSHAKE_INCOMPLETE"] * 4,
    "UNEXPECTED_SEQUENCE",
    "HANDSHAKE_COMPLETE",
    "HANDSHAKE_TIMEOUT",
    "INSUFFICIENT_EVIDENCE",
    "HANDSHAKE_COMPLETE",
]
plans = []
for i, ((name, events), outcome) in enumerate(zip(fixtures.items(), expected), 1):
    filename = "handshake-" + name + ".json"
    (f / filename).write_text(json.dumps(events, indent=2) + "\n")
    plans.append(
        dict(
            id=f"P{i:02}",
            feature="WPA2 handshake " + name,
            fixture="v3/" + filename,
            preconditions=["C++17 engine", "Synthetic metadata; no crypto proof"],
            expected=[outcome],
            kind="handshake",
            expected_sessions=2 if name == "concurrent" else 1,
        )
    )
for i, name in enumerate(
    [
        "controller_delay",
        "stale_controller",
        "missing_management",
        "client_ap_mismatch",
    ],
    1,
):
    events = [
        dict(
            event_id="ap_join",
            timestamp_us=100000,
            client="clientA",
            ap="apA",
            kind="assoc_ok",
            origin="ap",
            code=0,
        ),
        dict(
            event_id="client_view",
            timestamp_us=200000,
            client="clientA",
            ap="apA",
            kind="client_update",
            origin="client",
            reported_state="connected",
        ),
    ]
    outcome = "CONTROLLER_UPDATE_DELAY"
    if name == "controller_delay":
        events.append(
            dict(
                event_id="controller_view",
                timestamp_us=8000000,
                client="clientA",
                ap="apA",
                kind="controller_update",
                origin="controller",
                reported_state="connected",
            )
        )
    elif name == "stale_controller":
        events += [
            dict(
                event_id="ap_leave",
                timestamp_us=300000,
                client="clientA",
                ap="apA",
                kind="deauth",
                origin="ap",
                code=3,
            ),
            dict(
                event_id="client_leave",
                timestamp_us=350000,
                client="clientA",
                ap="apA",
                kind="client_update",
                origin="client",
                reported_state="disconnected",
            ),
            dict(
                event_id="controller_stale",
                timestamp_us=400000,
                client="clientA",
                ap="apA",
                kind="controller_update",
                origin="controller",
                reported_state="connected",
            ),
            dict(
                event_id="dashboard_stale",
                timestamp_us=500000,
                client="clientA",
                ap="apA",
                kind="dashboard_update",
                origin="synthetic",
                reported_state="connected",
            ),
        ]
        outcome = "STALE_OR_INCONSISTENT_CONTROLLER"
    elif name == "missing_management":
        outcome = "MISSING_MANAGEMENT_EVIDENCE"
    else:
        events[1]["reported_state"] = "disconnected"
        events.append(
            dict(
                event_id="controller_ok",
                timestamp_us=400000,
                client="clientA",
                ap="apA",
                kind="controller_update",
                origin="controller",
                reported_state="connected",
            )
        )
        outcome = "CLIENT_AP_MISMATCH"
    filename = name + ".json"
    (f / filename).write_text(json.dumps(events, indent=2) + "\n")
    plans.append(
        dict(
            id=f"C{i:02}",
            feature=name,
            fixture="v3/" + filename,
            preconditions=["Simulated common-clock event views"],
            expected=[outcome],
            kind="layers",
        )
    )
old = json.loads((r / "wireless-lab/scenarios/catalog.json").read_text())
for d in reversed(old):
    plans.insert(
        0,
        dict(
            id=d["id"],
            feature=d["title"],
            fixture=d["fixture"],
            preconditions=d["preconditions"],
            expected=d["expected_classifications"],
            kind="legacy",
        ),
    )
for p in plans:
    p.update(
        reproduction=f"python wireless-lab/scripts/validate_v3.py --test {p['id']}",
        expected_behavior=p["expected"],
        evidence_origin="synthetic",
    )
(r / "wireless-lab/scenarios/test-plan-v3.json").write_text(
    json.dumps(
        {"version": 1, "name": "Cisco wireless feature validation", "cases": plans},
        indent=2,
    )
    + "\n"
)
# PCAPNG enhanced packet wrapper, Ethernet IP-only fixture, and deterministic medium/large captures.
ns = runpy.run_path(str(r / "wireless-lab/scripts/generate_fixtures.py"))
for n in [4, 100, 2000]:
    packets = [ns["key"]((i % 4) + 1, True) for i in range(n)]
    packets = [(i * 1000, p) for i, (_, p) in enumerate(packets)]
    ns["write_pcap"](f / f"ethernet-{n}.pcap", packets, 1)
ns["write_pcap"](
    f / "ethernet-ip-only.pcap",
    [
        (
            0,
            bytes.fromhex("0200000010010200000001010800")
            + bytes.fromhex("450000140000000040010000c0000201c0000202"),
        )
    ],
    1,
)
raw = (r / "wireless-lab/fixtures/ethernet-eapol.pcap").read_bytes()


def block(kind, body):
    size = 12 + len(body)
    return struct.pack("<II", kind, size) + body + struct.pack("<I", size)


ng = block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1)) + block(
    1, struct.pack("<HHI", 1, 0, 65535)
)
pos = 24
while pos < len(raw):
    sec, sub, cap, orig = struct.unpack_from("<IIII", raw, pos)
    pos += 16
    p = raw[pos : pos + cap]
    pos += cap
    t = sec * 1000000 + sub
    ng += block(
        6,
        struct.pack("<IIIII", 0, t >> 32, t & 0xFFFFFFFF, cap, orig)
        + p
        + b"\0" * ((-cap) % 4),
    )
(f / "ethernet-eapol.pcapng").write_bytes(ng)
(f / "README.md").write_text(
    "All files are deterministic generated fixtures, not real network captures. JSON handshakes use header metadata only; key material is never included. PCAP EAPOL payloads use zero placeholders. P01–P10 are development scenarios; held-out evaluation is generated separately with a fixed seed. Ethernet captures contain no radio association evidence.\n"
)

(f / "manifest.json").write_text(
    json.dumps(
        [
            {
                "file": p.name,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "origin": "synthetic_generated",
            }
            for p in sorted(f.iterdir())
            if p.suffix in (".json", ".pcap", ".pcapng") and p.name != "manifest.json"
        ],
        indent=2,
    )
    + "\n"
)
