"""Real HTTP short-window evaluation. Requires a loopback native API and FAULT_TOKEN.
Ground truth is declared BEFORE traffic, independent of detector output.
This is scenario-level evaluation, not a production reliability benchmark.
"""

import argparse
import concurrent.futures
import json
import math
import os
import statistics
import threading
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = [
    ("baseline", "development", "none", 0, 1, False),
    ("latency-spike", "development", "latency", 750, 1, True),
    ("server-errors", "development", "http500", 0, 1, True),
    ("database-simulation", "development", "database", 0, 1, True),
    ("dependency-timeout", "development", "dependency", 600, 1, True),
    ("noisy-warning", "development", "warning", 0, 1, False),
    ("heldout-baseline", "held-out", "none", 0, 1, False),
    ("unseen-delay-950ms", "held-out", "latency", 950, 1, True),
    ("unseen-errors-every-3", "held-out", "http500", 0, 3, True),
    ("repeated-database-fault", "held-out", "database", 0, 2, True),
    ("dependency-recovery-800ms", "held-out", "dependency", 800, 2, True),
    ("heldout-noisy-warning", "held-out", "warning", 0, 3, False),
]


def wilson(success, n):
    if not n:
        return None
    z = 1.96
    p = success / n
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(mid - half, 4), round(mid + half, 4)]


def score(runs):
    tp = sum(r["expected_impact"] and r["detected"] for r in runs)
    fp = sum(not r["expected_impact"] and r["detected"] for r in runs)
    fn = sum(r["expected_impact"] and not r["detected"] for r in runs)
    return {
        "completed_experiments": len(runs),
        "true_positives": tp,
        "false_alerts": fp,
        "false_negatives": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "precision_wilson_95": wilson(tp, tp + fp),
        "recall_wilson_95": wilson(tp, tp + fn),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--duration", type=float, default=4)
    args = parser.parse_args()
    if not args.url.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise SystemExit("Only loopback test targets permitted")
    token = os.environ["FAULT_TOKEN"]
    headers = {"X-Lab-Token": token}
    client = httpx.Client(base_url=args.url, timeout=10, trust_env=False)
    window = client.get("/operations/summary").json()["window_seconds"]
    if window > 5:
        raise SystemExit(
            "Start with OBSERVATION_WINDOW_SECONDS=3 for accelerated evaluation; use a fresh evidence database."
        )
    runs, raw = [], []
    for name, split, kind, delay, every, truth in SCENARIOS:
        before = {i["id"] for i in client.get("/operations/incidents").json()}
        client.post(
            "/operations/faults",
            headers=headers,
            json={
                "kind": kind,
                "delay_ms": delay,
                "every": every,
                "duration_seconds": 30,
            },
        ).raise_for_status()
        started = time.time()
        samples = []
        lock = threading.Lock()

        def traffic(stop):
            with httpx.Client(
                base_url=args.url, timeout=10, trust_env=False
            ) as traffic_client:
                while time.time() < stop:
                    at = time.time()
                    r = traffic_client.get("/events")
                    with lock:
                        samples.append(
                            {
                                "at": at,
                                "duration": time.time() - at,
                                "status": r.status_code,
                            }
                        )
                    time.sleep(0.04)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(traffic, started + args.duration) for _ in range(4)]
            for f in futures:
                f.result()
        detected = [
            i
            for i in client.get("/operations/incidents").json()
            if i["id"] not in before
        ]
        cleared = time.time()
        client.post(
            "/operations/faults", headers=headers, json={"kind": "none"}
        ).raise_for_status()
        recovery_status = []
        until = time.time() + window + 1.5
        while time.time() < until:
            recovery_status.append(client.get("/events").status_code)
            time.sleep(0.05)
        final = client.get("/operations/incidents").json()
        matching = [i for i in final if i["id"] not in before]
        ended = [i["end"] for i in matching if i["end"]]
        latencies = sorted(s["duration"] for s in samples)
        n = len(samples)
        success = sum(s["status"] < 500 for s in samples)
        run = {
            "scenario": name,
            "split": split,
            "kind": kind,
            "delay_ms": delay,
            "every": every,
            "expected_impact": truth,
            "detected": bool(detected),
            "requests": n,
            "success_rate": success / n,
            "success_wilson_95": wilson(success, n),
            "p95_seconds": latencies[math.ceil(n * 0.95) - 1],
            "detection_seconds": min(i["start"] for i in detected) - started
            if detected
            else None,
            "recovery_seconds": max(ended) - cleared
            if matching and len(ended) == len(matching)
            else None,
            "recovery_probe_success_rate": sum(x < 500 for x in recovery_status)
            / len(recovery_status),
        }
        runs.append(run)
        raw.append(
            {
                "scenario": name,
                "started": started,
                "fault_cleared": cleared,
                "samples": samples,
                "incidents": matching,
            }
        )
        print(json.dumps(run), flush=True)
    # Offline scenario-level screening compares fixed thresholds on the same observations.
    # It does not claim to replay time-to-alert, hold periods, or Prometheus rules.
    configs = []
    for config, error_limit, latency_limit in [
        ("local-window-v1", 0.05, 0.5),
        ("conservative-offline", 0.2, 1.0),
    ]:
        classified = [
            {
                **r,
                "detected": r["requests"] >= 5
                and (
                    1 - r["success_rate"] > error_limit
                    or r["p95_seconds"] > latency_limit
                ),
            }
            for r in runs
        ]
        configs.append(
            {
                "configuration": config,
                "mode": "offline scenario aggregate; no timing replay",
                **score(classified),
            }
        )
    result = {
        "source": "Real HTTP local experiments; short 3s window; scenario-level labels; database faults simulated",
        "summary": score(runs),
        "splits": {
            s: score([r for r in runs if r["split"] == s])
            for s in ["development", "held-out"]
        },
        "configuration_comparison": configs,
        "timing": {
            "median_detection_seconds": statistics.median(
                [
                    r["detection_seconds"]
                    for r in runs
                    if r["detection_seconds"] is not None
                ]
            )
        },
        "runs": runs,
    }
    (ROOT / "evidence/experiments.json").write_text(json.dumps(result, indent=2))
    (ROOT / "evidence/raw-experiments.json").write_text(json.dumps(raw, indent=2))
    print(json.dumps(result["summary"]), flush=True)


if __name__ == "__main__":
    main()
