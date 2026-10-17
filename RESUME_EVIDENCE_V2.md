# Revised Cvent SRE bullets — v2

These three bullets use executed local checks or directly inspectable code; they do not claim AWS deployment, unmeasured automatic recovery or successful new CI before its run is verified.

- Validated reliability and registration behavior through 46 passing Python tests by adding real Bash-to-FastAPI smoke checks and testing capacity, idempotency, readiness, instrumentation and local fault safety; one PostgreSQL integration test remained skipped locally.
- Expanded observability to 15 Grafana panels by adding request success, p50 latency, target availability, latency compliance and availability error-budget queries with explicit no-traffic handling and zero-initialized server-error counters.
- Built an independently running UTC experiment observer and six Bash operations scripts by separating health failures, Prometheus observations, alert states and manual-versus-crash recovery evidence, with ShellCheck validation and opt-in isolated Compose execution.

| Bullet | Supporting evidence | Limit |
|---|---|---|
| 46 tests | evidence/v2/backend-junit.xml; backend-tests.txt; backend/tests/test_v2_automation.py | Native execution uses SQLite; remote CI PostgreSQL result must be checked separately |
| 15 panels | monitoring/grafana/dashboards/eventpulse.json; test_monitoring_panels_use_actual_metric_expressions | Panel configuration is inspected; runtime validation comes from the actual stack/CI |
| Observer + Bash | scripts/reliability.py; six scripts/*.sh including shared lib.sh; ShellCheck output; real Bash smoke test | Building a recovery observer does not itself establish a measured restart duration |

Existing main baseline CI success is independently verified at commit 0a6efd1 in run 38942106723. Consult docs/VERIFICATION_REPORT.md for the current v2 run, exact SHA and any measured Docker recovery results before strengthening claims.
