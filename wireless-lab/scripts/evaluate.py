"""Reproducible development benchmark; no live wireless or external network access."""

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from wirelesslab.analyze import analyze_events  # noqa: E402
from wirelesslab.scenarios import run_scenario  # noqa: E402
from wirelesslab.packets import parse_capture  # noqa: E402


def summary(values):
    ordered = sorted(values)
    return {
        "repetitions": len(values),
        "median_ms": statistics.median(values),
        "p95_ms": ordered[math.ceil(0.95 * len(values)) - 1],
        "max_ms": max(values),
        "samples_ms": values,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite historical measurements")
    report = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(),
            "cpu": next(
                (
                    line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")
                ),
                "unknown",
            ),
        },
        "scope": "Synthetic fixtures; development container; sequential warm workloads; not production or Cisco-scale",
        "workloads": {},
    }
    for name, scenario in [("normal", "E"), ("missing", "I"), ("reordered", "H")]:
        fixture = [
            {k: v for k, v in e.items() if k != "explanation"}
            for e in run_scenario(scenario)["events"]
        ]
        values = [analyze_events(fixture)["analysis_duration_ms"] for _ in range(20)]
        report["workloads"][name] = {
            "events": len(fixture),
            "stage": "Python validation + C++ launch, IPC and analysis",
            **summary(values),
        }
    fixture = [
        {k: v for k, v in e.items() if k != "explanation"}
        for e in run_scenario("E")["events"][:4]
    ]
    large = fixture + [
        {
            "event_id": f"data_{i}",
            "timestamp_us": 1700000000400000 + i,
            "client": fixture[0]["client"],
            "ap": fixture[0]["ap"],
            "kind": "data",
            "origin": "synthetic",
        }
        for i in range(9996)
    ]
    values = []
    for _ in range(10):
        start = time.perf_counter()
        result = analyze_events(large)
        values.append((time.perf_counter() - start) * 1000)
        assert result["processed_events"] == 10000
    report["workloads"]["large"] = {
        "events": 10000,
        "stage": "End-to-end Python validation + serialization + C++ process + JSON parse",
        **summary(values),
        "median_events_per_second": 10000 / (statistics.median(values) / 1000),
    }
    packet = (ROOT / "fixtures/association-success.pcap").read_bytes()
    parse_capture(packet, "fixture.pcap", False)  # Warm field discovery separately.
    values = [
        parse_capture(packet, "fixture.pcap", False)["parsing_duration_ms"]
        for _ in range(10)
    ]
    report["workloads"]["pcap"] = {
        "bytes": len(packet),
        "packets": 11,
        "stage": "Warm TShark file extraction + normalization, excludes cached -G field discovery",
        **summary(values),
    }
    with tempfile.TemporaryDirectory() as temporary:
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{temporary}/api.db",
            "PYTHONPATH": str(ROOT.parent / "backend"),
        }
        with open(Path(temporary) / "server.log", "w") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.server:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "18001",
                ],
                cwd=ROOT.parent,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                with httpx.Client(
                    base_url="http://127.0.0.1:18001", trust_env=False, timeout=15
                ) as client:
                    for _ in range(100):
                        try:
                            if client.get("/health/ready").status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.1)
                    else:
                        raise RuntimeError("Benchmark API did not start")
                    assert (
                        client.post(
                            "/wireless-lab/guest", headers={"X-Wireless-Demo": "1"}
                        ).status_code
                        == 201
                    )
                    created = client.post(
                        "/wireless-lab/runs",
                        headers={"X-Wireless-Demo": "1"},
                        json={"scenario_id": "E"},
                    )
                    assert created.status_code == 201
                    url = "/wireless-lab/runs/" + created.json()["id"]
                    values = []
                    for _ in range(50):
                        start = time.perf_counter()
                        response = client.get(url)
                        values.append((time.perf_counter() - start) * 1000)
                        assert (
                            response.status_code == 200
                            and response.json()["verdict"] == "pass"
                        )
                    report["workloads"]["api_read"] = {
                        "stage": "Real loopback HTTP GET owned scenario-E report; SQLite; 1 client; 1 in-flight; persistent connection; no analysis in read",
                        **summary(values),
                    }
            finally:
                process.terminate()
                process.wait(timeout=10)
    report["memory"] = {
        "peak_child_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "scope": "Linux cumulative peak RSS of a single child across this benchmark (TShark, analyzer or API); not isolated C++ heap or summed memory",
    }
    outcomes = [run_scenario(s) for s in "ABCDEFGHIJ"]
    report["classification"] = {
        "executed": len(outcomes),
        "correct": sum(r["verdict"] == "pass" for r in outcomes),
        "false_classifications": sum(r["verdict"] != "pass" for r in outcomes),
        "scope": "Ten designed fixtures only; no real-world accuracy estimate",
    }
    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "workloads"}))


if __name__ == "__main__":
    main()
