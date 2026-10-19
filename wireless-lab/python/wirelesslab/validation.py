import json
import time
from .analyze import LAB_ROOT, analyze_events, analyze_handshakes
from .schema import WirelessEvent
from .scenarios import run_scenario
from .layers import correlate_layers


def plans():
    return json.loads((LAB_ROOT / "scenarios/test-plan-v3.json").read_text())


def clean_events(events):
    return [
        WirelessEvent.model_validate(
            {k: v for k, v in e.items() if k != "explanation"}
        ).model_dump()
        for e in events
    ]


def execute_case(identifier):
    case = next((p for p in plans()["cases"] if p["id"] == identifier), None)
    if case is None:
        raise ValueError("Unknown registered test ID")
    start = time.perf_counter()
    if case["kind"] == "legacy":
        result = run_scenario(identifier)
        events = clean_events(result["events"])
        observed = result["actual_classifications"]
        details = result["analysis"]
    else:
        events = clean_events(
            json.loads((LAB_ROOT / "fixtures" / case["fixture"]).read_text())
        )
        if case["kind"] == "handshake":
            details = analyze_handshakes(events)
            observed = sorted({s["classification"] for s in details["sessions"]})
        else:
            details = correlate_layers(events)
            observed = sorted({s["classification"] for s in details["clients"]})
    passed = observed == sorted(case["expected"])
    if "expected_sessions" in case:
        passed = passed and len(details["sessions"]) == case["expected_sessions"]
    return {
        "test_id": identifier,
        "feature": case["feature"],
        "preconditions": case["preconditions"],
        "input_evidence": case["fixture"],
        "expected_behavior": case["expected"],
        "observed_behavior": observed,
        "verdict": "pass" if passed else "fail",
        "root_cause_classification": observed,
        "event_references": [e["event_id"] for e in events],
        "execution_duration_ms": (time.perf_counter() - start) * 1000,
        "reproduction": case["reproduction"],
        "details": details,
        "evidence_origin": "synthetic",
        "handshakes": analyze_handshakes(events)
        if case["kind"] != "handshake"
        else details,
        "layers": correlate_layers(events),
    }


def execute_plan(test_id=None):
    cases = [test_id] if test_id else [p["id"] for p in plans()["cases"]]
    results = []
    started = time.monotonic()
    for c in cases:
        if time.monotonic() - started > 30:
            from .analyze import AnalyzerUnavailable

            raise AnalyzerUnavailable("Test-plan deadline exceeded")
        results.append(execute_case(c))
    return {
        "unique_scenarios": len(set(cases)),
        "executed_runs": len(results),
        "passed_runs": sum(r["verdict"] == "pass" for r in results),
        "validation_failures": sum(r["verdict"] == "fail" for r in results),
        "results": results,
        "evidence_origin": "synthetic",
        "plan_version": 1,
    }


def import_capture(data, filename):
    from .packets import parse_capture

    start = time.perf_counter()
    extraction = parse_capture(data, filename, pseudonymize=True, allow_empty=True)
    events = extraction.pop("events")
    association = analyze_events(events)
    return {
        "scenario": {
            "id": "capture-import",
            "title": "Private capture import",
            "evidence_type": extraction["origin"],
            "expected_classifications": [],
        },
        "verdict": "analysis_only",
        "actual_classifications": sorted(
            {c["classification"] for c in association["clients"]}
        ),
        "events": events,
        "analysis": association,
        "handshakes": analyze_handshakes(
            events, observed_until_us=extraction["observed_until_us"]
        ),
        "layers": correlate_layers(events),
        "extraction": extraction,
        "total_duration_ms": (time.perf_counter() - start) * 1000,
        "mode": "Imported file; origin unverified unless matched to known synthetic fixture; no raw bytes retained",
    }
