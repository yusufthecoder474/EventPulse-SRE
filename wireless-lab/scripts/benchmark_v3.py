"""Development-only sequential measurements; no wireless interface or external traffic."""

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
from wirelesslab.validation import import_capture, execute_plan  # noqa: E402


def summary(values):
    order = sorted(values)
    return {
        "repetitions": len(values),
        "p50_ms": statistics.median(values),
        "p95_ms": order[math.ceil(0.95 * len(order)) - 1],
        "max_ms": max(values),
        "samples_ms": values,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args()
    if a.output.exists():
        raise SystemExit("Refusing to overwrite measurements")
    report = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(),
            "cpu": next(
                (
                    x.split(":", 1)[1].strip()
                    for x in Path("/proc/cpuinfo").read_text().splitlines()
                    if x.startswith("model name")
                ),
                "unknown",
            ),
        },
        "method": "Sequential warm synthetic fixture imports. Nearest-rank p95; at seven samples p95 equals max. Not production, RF or real-capture performance.",
        "captures": {},
    }
    datasets = [
        ("small", "ethernet-4.pcap"),
        ("medium", "ethernet-100.pcap"),
        ("large_bounded", "ethernet-2000.pcap"),
    ]
    for label, name in datasets:
        data = (ROOT / "fixtures/v3" / name).read_bytes()
        import_capture(data, name)
        times = {
            k: []
            for k in [
                "pipeline",
                "tshark_normalization",
                "cpp_association_bridge",
                "cpp_handshake_bridge",
            ]
        }
        for _ in range(7):
            start = time.perf_counter()
            r = import_capture(data, name)
            times["pipeline"].append((time.perf_counter() - start) * 1000)
            times["tshark_normalization"].append(r["extraction"]["parsing_duration_ms"])
            times["cpp_association_bridge"].append(
                r["analysis"]["analysis_duration_ms"]
            )
            times["cpp_handshake_bridge"].append(
                r["handshakes"]["analysis_duration_ms"]
            )
            assert r["extraction"]["packet_count"] == int(
                name.split("-")[1].split(".")[0]
            )
        report["captures"][label] = {
            "bytes": len(data),
            "packets": r["extraction"]["packet_count"],
            "metrics": {k: summary(v) for k, v in times.items()},
            "pipeline_median_packets_per_second": r["extraction"]["packet_count"]
            / (statistics.median(times["pipeline"]) / 1000),
        }
    for label, test_id in [("single_scenario", "P01"), ("full_plan", None)]:
        values = []
        for _ in range(5):
            start = time.perf_counter()
            r = execute_plan(test_id)
            values.append((time.perf_counter() - start) * 1000)
            assert r["validation_failures"] == 0
        report[label] = {
            "unique_scenarios_per_execution": r["unique_scenarios"],
            "executed_runs_per_execution": r["executed_runs"],
            **summary(values),
        }
    with tempfile.TemporaryDirectory() as temporary:
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{temporary}/bench.db",
            "PYTHONPATH": str(ROOT.parent / "backend"),
        }
        with (Path(temporary) / "server.log").open("w") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.server:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "18003",
                ],
                cwd=ROOT.parent,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        if (
                            httpx.get(
                                "http://127.0.0.1:18003/health/ready", trust_env=False
                            ).status_code
                            == 200
                        ):
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Benchmark API not ready")
                report["http_import"] = {}
                for label, name in datasets:
                    with httpx.Client(
                        base_url="http://127.0.0.1:18003", trust_env=False, timeout=30
                    ) as client:
                        assert (
                            client.post(
                                "/wireless-lab/guest", headers={"X-Wireless-Demo": "1"}
                            ).status_code
                            == 201
                        )
                        data = (ROOT / "fixtures/v3" / name).read_bytes()
                        values = []
                        for _ in range(7):
                            start = time.perf_counter()
                            r = client.post(
                                "/wireless-lab/imports",
                                headers={
                                    "X-Wireless-Demo": "1",
                                    "X-Lab-Authorized": "true",
                                    "X-File-Name": name,
                                },
                                content=data,
                            )
                            values.append((time.perf_counter() - start) * 1000)
                            assert r.status_code == 201, r.text
                        report["http_import"][label] = summary(values)
            finally:
                process.terminate()
                process.wait(timeout=10)
    report["http_scope"] = (
        "Real loopback HTTP POST /wireless-lab/imports, one guest/client per size, one request in flight, SQLite, includes parser, both C++ bridges, database save and JSON response. Separate from direct pipeline/bridge timings. First HTTP import includes cold TShark field discovery; following imports use cached field selection."
    )
    report["memory"] = {
        "peak_reaped_child_rss_kib": resource.getrusage(
            resource.RUSAGE_CHILDREN
        ).ru_maxrss,
        "scope": "Linux maximum RSS reported for reaped benchmark child workloads, including TShark/analyzer/API; not isolated C++ heap, summed deployment memory or a leak measurement.",
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({k: v for k, v in report.items() if k in ["memory", "environment"]})
    )


if __name__ == "__main__":
    main()
