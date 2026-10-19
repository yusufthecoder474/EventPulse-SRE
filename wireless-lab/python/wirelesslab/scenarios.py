import json
import time
from .analyze import LAB_ROOT, analyze_events
from .packets import parse_capture
from .schema import WirelessEvent, explain


def definitions():
    return json.loads((LAB_ROOT / "scenarios/catalog.json").read_text())


def scenario(identifier):
    found = next((s for s in definitions() if s["id"] == identifier), None)
    if found is None:
        raise ValueError("Unknown approved scenario")
    return found


def run_scenario(identifier):
    definition = scenario(identifier)
    start = time.perf_counter()
    fixture = LAB_ROOT / "fixtures" / definition["fixture"]
    if definition["evidence_type"] == "generated_pcap":
        extraction = parse_capture(
            fixture.read_bytes(), fixture.name, pseudonymize=False
        )
        events = extraction["events"]
    else:
        extraction = {
            "parsing_duration_ms": None,
            "limitations": [
                "Synthetic event fixture, not packet or hardware evidence."
            ],
        }
        events = [
            WirelessEvent.model_validate(e).model_dump()
            for e in json.loads(fixture.read_text())
        ]
    analysis = analyze_events(events)
    actual = sorted({c["classification"] for c in analysis["clients"]})
    expected = definition["expected_classifications"]
    assertions = {
        "classification_matches": actual == sorted(expected),
        "duplicate_handling": analysis["duplicate_events"]
        >= definition.get("min_duplicates", 0),
        "out_of_order_handling": analysis["out_of_order_pairs"]
        >= definition.get("min_out_of_order", 0),
    }
    events = [
        {**e, "explanation": explain(WirelessEvent.model_validate(e))} for e in events
    ]
    return {
        "scenario": definition,
        "actual_classifications": actual,
        "verdict": "pass" if all(assertions.values()) else "fail",
        "assertions": assertions,
        "events": events,
        "analysis": analysis,
        "extraction": {k: v for k, v in extraction.items() if k != "events"},
        "total_duration_ms": (time.perf_counter() - start) * 1000,
        "mode": "synthetic laboratory; no hardware integration",
    }


def approved_capture(identifier):
    definition = scenario(identifier)
    if definition["evidence_type"] != "generated_pcap":
        raise ValueError("This scenario uses JSON events, not a packet capture")
    return LAB_ROOT / "fixtures" / definition["fixture"]
