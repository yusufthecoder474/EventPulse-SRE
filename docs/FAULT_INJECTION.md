# v2 timestamped reliability experiments

Preserve the original root FAULT_INJECTION.md and POSTMORTEM.md. Historical manual evidence remains distinct from new machine observations.

Create a **disposable** Compose project, never reuse a personal shared stack:

```bash
export COMPOSE_PROJECT_NAME=eventpulse-v2-demo
export ENABLE_PROCESS_CRASH_TEST=true  # isolated local/CI experiment only
python scripts/bootstrap.py
docker compose up --build -d --wait --wait-timeout 180
sleep 12
bash scripts/verify-stack.sh
python scripts/reliability.py --scenario api-crash --project "$COMPOSE_PROJECT_NAME" --allow-local-faults
python scripts/reliability.py --scenario database-outage --project "$COMPOSE_PROJECT_NAME" --allow-local-faults --hold-seconds 12
python scripts/reliability.py --scenario api-outage --project "$COMPOSE_PROJECT_NAME" --allow-local-faults --hold-seconds 45
```

The tool checks loopback URLs, running target identity, Compose project labels, baseline readiness and restart policy. It requires an explicit flag and project prefix eventpulse-v2-. It never uses AWS APIs. It sends continuous synthetic GET /events requests and independently polls readiness and Prometheus. Output filenames are timestamped and refuse overwrite. Manual stop/start scenarios clean up by restarting the dependency even on failure.

| Scenario | Mechanism | Recovery classification |
|---|---|---|
| api-crash | Docker exec sends SIGUSR1 to an explicitly enabled handler; API exits abruptly with code 86 | Automatic only if RestartCount increases and fresh readiness succeeds |
| api-outage | docker compose stop api, hold, start api | Manual; permits observation of the 30s target-down alert |
| database-outage | docker compose stop db, hold, start db | Manual DB restoration and application reconnection |
| Latency / HTTP 5xx | Existing token/TTL native lab | Prior synthetic evidence; v2 real-Compose observer does not enable lab mutations |
| Delayed actual database response | Not injected | NOT VERIFIED; no host network shaping or destructive DB workload |

Docker's unless-stopped restart policy applies to process exit, not an unhealthy status or an explicit compose stop. Health checks do not restart containers. The crash test signals only PID 1 **inside the selected existing local API container**; it does not kill a host process. The registered local handler calls os._exit(86), bypassing cleanup. ENABLE_PROCESS_CRASH_TEST is false by default and requires APP_ENV=local on POSIX; no HTTP crash endpoint exists. The observer refuses execution without that explicit opt-in. The first CI attempt sent SIGKILL inside the PID namespace but did not terminate PID 1; the failed trial is preserved. Let the container run >10 seconds before the crash test. The normal UI/Compose fault lab remains disabled.

## Timestamp semantics

Every event uses host-observed UTC ISO8601 microseconds. `fault_action_requested_at` is the command request time, not the exact kernel death time. `process_failure_at` is Docker's die-event timestamp when available. `container_restart_observed_at` is when the host sees RestartCount increase. `first_failed_health_check_at`, `first_prometheus_failure_at`, `alert_firing_at`, `recovery_action_at`, `first_successful_health_check_at` and `alert_resolution_at` are separate observations.

Prometheus scrape/evaluation timestamps are sampled; the observer reports first *observed* failure/firing/resolution, not a stronger exact internal event time. Polling/transport delay and host wall-clock adjustments affect timing. Null means not observed or not applicable, never zero seconds. A fast process restart may finish between scrapes and therefore produce no Prometheus failure or alert. That is not silently counted as an alerting pass.

Health detection is measured from fault command request to first failed readiness. Alert detection has its own interval. Automatic recovery uses Docker die event to fresh readiness, and remains null if death was not observed. Manual restoration uses explicit start action to fresh readiness. Alert resolution occurs separately after restoration. Request totals include baseline, outage and recovery samples over the bounded experiment; p50/p95 include durations of failures as well as successes. No availability SLA is inferred.
