"""Held-out synthetic metadata evaluation; no real-world accuracy claim."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from wirelesslab.analyze import analyze_handshakes  # noqa: E402


def dataset():
    rng = random.Random(73129)
    rows = []
    kinds = [
        "complete",
        "missing1",
        "missing2",
        "missing3",
        "missing4",
        "reordered",
        "retransmitted",
        "timeout",
        "insufficient",
        "concurrent",
    ]
    for kind in kinds:
        for repetition in range(12):
            base = rng.randrange(100, 2**32)
            delta = rng.randrange(1, 100)
            start = rng.randrange(1_000_000, 1_000_000_000)
            gap = rng.randrange(2000, 100000)

            def event(m, client="heldout_client"):
                return dict(
                    event_id=f"h_{kind}_{repetition}_{client}_{m}",
                    timestamp_us=start + gap * m,
                    client=client,
                    ap="heldout_authenticator",
                    authenticator="heldout_authenticator",
                    kind=f"eapol_{m}",
                    direction="ap_to_client" if m in (1, 3) else "client_to_ap",
                    replay_counter=str(base if m < 3 else base + delta),
                    key_info={1: 138, 2: 266, 3: 970, 4: 778}[m],
                    descriptor_type=2,
                    origin="synthetic",
                )

            events = [event(m) for m in range(1, 5)]
            expected = "HANDSHAKE_COMPLETE"
            sessions = 1
            if kind.startswith("missing"):
                events.pop(int(kind[-1]) - 1)
                expected = "HANDSHAKE_INCOMPLETE"
            elif kind == "reordered":
                events[1]["timestamp_us"] = start + gap * 3 + gap // 2
                expected = "UNEXPECTED_SEQUENCE"
            elif kind == "retransmitted":
                retry = event(2)
                retry["event_id"] += "_retry"
                retry["timestamp_us"] += gap // 2
                events.append(retry)
            elif kind == "timeout":
                events = events[:2] + [
                    dict(
                        event_id=f"tail_{repetition}",
                        timestamp_us=start + 8_000_000,
                        client="heldout_client",
                        ap="heldout_authenticator",
                        kind="data",
                        origin="synthetic",
                    )
                ]
                expected = "HANDSHAKE_TIMEOUT"
            elif kind == "insufficient":
                for e in events:
                    e.pop("replay_counter")
                expected = "INSUFFICIENT_EVIDENCE"
                sessions = 4
            elif kind == "concurrent":
                events += [event(m, "second_client") for m in range(1, 5)]
                sessions = 2
            rng.shuffle(events)
            rows.append(
                {
                    "id": f"heldout_{kind}_{repetition}",
                    "expected": expected,
                    "expected_sessions": sessions,
                    "events": events,
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args()
    if a.output.exists():
        raise SystemExit("Refusing to overwrite evidence")
    data = dataset()
    results = []
    for row in data:
        result = analyze_handshakes(row["events"])
        actual = sorted({s["classification"] for s in result["sessions"]})
        results.append(
            {
                "id": row["id"],
                "expected": row["expected"],
                "actual": actual,
                "session_count": len(result["sessions"]),
                "passed": actual == [row["expected"]]
                and len(result["sessions"]) == row["expected_sessions"],
            }
        )
    serialized = json.dumps(data, sort_keys=True)
    report = {
        "seed": 73129,
        "dataset_size": len(data),
        "correct": sum(x["passed"] for x in results),
        "mismatches": sum(not x["passed"] for x in results),
        "dataset_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
        "scope": "Held-out synthetic metadata variants, separate from development fixture files; no real captures, real-world accuracy or cryptographic verification",
        "results": results,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n")
    a.output.with_name(a.output.stem + "-inputs.json").write_text(
        json.dumps(data, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "results"}))
    raise SystemExit(1 if report["mismatches"] else 0)


if __name__ == "__main__":
    main()
