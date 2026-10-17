"""Bounded LOCAL Compose experiment with independent UTC observation events.
No AWS APIs. Requires explicit project/permission flags and healthy baseline.
A stop/start is manual recovery; only exec-killing PID 1 tests automatic restart.
"""

import argparse
import concurrent.futures
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]


def utc(timestamp=None):
    return datetime.fromtimestamp(timestamp or time.time(), timezone.utc).isoformat(
        timespec="microseconds"
    )


def probe(url):
    started = time.monotonic()
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=1) as response:
            return response.status, time.monotonic() - started, response.read()
    except urllib.error.HTTPError as error:
        return error.code, time.monotonic() - started, b""
    except OSError:
        return None, time.monotonic() - started, b""


def prom_value(base, expression):
    status, _, data = probe(
        base + "/api/v1/query?" + urllib.parse.urlencode({"query": expression})
    )
    if status != 200:
        return None
    result = json.loads(data).get("data", {}).get("result", [])
    return float(result[0]["value"][1]) if result else None


def summarize(samples):
    values = sorted(s["duration_seconds"] for s in samples)
    n = len(samples)
    import math

    return {
        "total_requests": n,
        "successful_requests": sum(s["status"] == 200 for s in samples),
        "failed_requests": sum(s["status"] != 200 for s in samples),
        "error_percentage": 100 * sum(s["status"] != 200 for s in samples) / n
        if n
        else None,
        "p50_seconds": values[math.ceil(n * 0.5) - 1] if n else None,
        "p95_seconds": values[math.ceil(n * 0.95) - 1] if n else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=["api-crash", "api-outage", "database-outage"],
        required=True,
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--allow-local-faults", action="store_true")
    parser.add_argument("--hold-seconds", type=float, default=45)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.allow_local_faults or not args.project.startswith("eventpulse-v2-"):
        parser.error(
            "Explicit --allow-local-faults and an isolated eventpulse-v2-* project are required"
        )
    if not 0 <= args.hold_seconds <= 120 or not 5 <= args.timeout <= 180:
        parser.error("Hold must be 0..120s; timeout must be 5..180s")
    api = os.getenv("API_URL", "http://127.0.0.1:8000")
    prom = os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090")
    for url in (api, prom):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
            parser.error("Use loopback URLs only")
    compose = [
        "docker",
        "compose",
        "--project-directory",
        str(ROOT),
        "-f",
        str(ROOT / "compose.yml"),
        "-p",
        args.project,
    ]

    def run(command, check=True):
        return subprocess.run(command, capture_output=True, text=True, check=check)

    service = "db" if args.scenario == "database-outage" else "api"
    container = run(compose + ["ps", "-q", service]).stdout.strip()
    if not container:
        raise SystemExit("Expected running target not found")
    baseline = json.loads(run(["docker", "inspect", container]).stdout)[0]
    if baseline["Config"]["Labels"].get("com.docker.compose.project") != args.project:
        raise SystemExit("Project label mismatch")
    if probe(api + "/health/ready")[0] != 200:
        raise SystemExit("Baseline API is not ready")
    if (
        args.scenario == "api-crash"
        and baseline["HostConfig"]["RestartPolicy"]["Name"] != "unless-stopped"
    ):
        raise SystemExit("Expected unless-stopped policy")
    if args.scenario == "api-crash" and "ENABLE_PROCESS_CRASH_TEST=true" not in baseline["Config"].get("Env", []):
        raise SystemExit("Explicit ENABLE_PROCESS_CRASH_TEST=true required on isolated local API")
    counter = baseline["RestartCount"]
    events = []
    samples = []
    stop = threading.Event()
    lock = threading.Lock()
    result = {
        "scenario": args.scenario,
        "project": args.project,
        "recovery_mode": "automatic Docker restart"
        if args.scenario == "api-crash"
        else "manual start",
        "sample_interval_seconds": 0.1,
        "events": events,
        "docker_restart_count_before": counter,
        "first_failed_health_check_at": None,
        "first_prometheus_failure_at": None,
        "alert_firing_at": None,
        "recovery_action_at": None,
        "first_successful_health_check_at": None,
        "alert_resolution_at": None,
        "process_failure_at": None,
        "container_restart_observed_at": None,
    }

    def event(name):
        with lock:
            if result.get(name) is None:
                result[name] = utc()
                events.append({"event": name, "observed_at": result[name]})

    failure_started = threading.Event()

    def traffic():
        while not stop.is_set():
            at = utc()
            status, duration, _ = probe(api + "/events")
            with lock:
                samples.append(
                    {"observed_at": at, "status": status, "duration_seconds": duration}
                )
            stop.wait(0.05)

    def observe():
        failed = False
        prom_failed = False
        while not stop.is_set():
            status, _, _ = probe(api + "/health/ready")
            if failure_started.is_set():
                if status != 200:
                    failed = True
                    event("first_failed_health_check_at")
                elif (failed or result["container_restart_observed_at"]) and result[
                    "first_successful_health_check_at"
                ] is None:
                    event("first_successful_health_check_at")
                expression = (
                    "eventpulse_database_ready"
                    if service == "db"
                    else 'up{job="eventpulse"}'
                )
                value = prom_value(prom, expression)
                if value == 0:
                    prom_failed = True
                    event("first_prometheus_failure_at")
                alert = (
                    prom_value(
                        prom,
                        'ALERTS{alertname="EventPulseTargetUnreachable",alertstate="firing"}',
                    )
                    if service == "api"
                    else None
                )
                if alert == 1:
                    event("alert_firing_at")
                elif result["alert_firing_at"] and value == 1:
                    event("alert_resolution_at")
                if service == "db" and prom_failed and value == 1:
                    event("prometheus_recovered_at")
            stop.wait(0.1)

    error = None
    manual_stopped = False
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        traffic_future = pool.submit(traffic)
        observe_future = pool.submit(observe)
        try:
            time.sleep(0.5)
            event("fault_action_requested_at")
            failure_started.set()
            if args.scenario == "api-crash":
                # Executed inside the existing container. The opt-in SIGUSR1 handler calls os._exit(86); manual docker stop/kill is NOT used.
                run(
                    compose
                    + [
                        "exec",
                        "-T",
                        "api",
                        "python",
                        "-c",
                        "import os,signal; os.kill(1,signal.SIGUSR1)",
                    ],
                    check=False,
                )
            else:
                run(compose + ["stop", "--timeout", "2", service])
                manual_stopped = True
                time.sleep(args.hold_seconds)
                event("recovery_action_at")
                run(compose + ["start", service])
                manual_stopped = False
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                current = json.loads(run(["docker", "inspect", container]).stdout)[0]
                if current["RestartCount"] > counter:
                    result["docker_restart_count_after"] = current["RestartCount"]
                    event("container_restart_observed_at")
                success = result["first_successful_health_check_at"]
                if success and (
                    args.scenario == "api-crash"
                    or (service == "db" and result.get("prometheus_recovered_at"))
                    or result["alert_resolution_at"]
                ):
                    break
                time.sleep(0.1)
            else:
                error = "Timed out waiting for required recovery observations"
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)
        finally:
            # Never leave a manually stopped local dependency stopped after a failed test.
            if manual_stopped:
                run(compose + ["start", service], check=False)
            stop.set()
        traffic_future.result()
        observe_future.result()
    end = time.time()
    docker_events = run(
        [
            "docker",
            "events",
            "--since",
            str(started),
            "--until",
            str(end),
            "--filter",
            "container=" + container,
            "--filter",
            "event=die",
            "--format",
            "{{json .}}",
        ],
        check=False,
    )
    for line in docker_events.stdout.splitlines():
        item = json.loads(line)
        if item.get("timeNano"):
            result["process_failure_at"] = utc(item["timeNano"] / 1e9)
            break

    def seconds(a, b):
        return (
            (
                datetime.fromisoformat(result[b]) - datetime.fromisoformat(result[a])
            ).total_seconds()
            if result.get(a) and result.get(b)
            else None
        )

    result.update(
        {
            "health_detection_seconds": seconds(
                "fault_action_requested_at", "first_failed_health_check_at"
            ),
            "prometheus_detection_seconds": seconds(
                "fault_action_requested_at", "first_prometheus_failure_at"
            ),
            "alert_detection_seconds": seconds(
                "fault_action_requested_at", "alert_firing_at"
            ),
            "automatic_recovery_seconds": seconds(
                "process_failure_at", "first_successful_health_check_at"
            )
            if args.scenario == "api-crash"
            else None,
            "manual_restoration_seconds": seconds(
                "recovery_action_at", "first_successful_health_check_at"
            ),
            "alert_resolution_seconds": seconds(
                "first_successful_health_check_at", "alert_resolution_at"
            ),
            "request_measurements": summarize(samples),
            "request_samples": samples,
            "status": "FAIL" if error else "PASS",
            "error": error,
            "notes": "Null means not observed or not applicable; a short crash may recover between Prometheus scrapes and never fire an alert.",
        }
    )
    if args.scenario == "api-crash" and not result["container_restart_observed_at"]:
        result["status"] = "FAIL"
        result["error"] = "Restart counter did not increase"
    output = args.output or ROOT / "evidence/v2" / (
        "reliability-"
        + args.scenario
        + "-"
        + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        + ".json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit("Refusing to overwrite existing evidence")
    output.write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("request_samples", "events")},
            indent=2,
        )
    )
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
