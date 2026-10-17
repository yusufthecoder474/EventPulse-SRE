# Reliability and performance report — v2

Historical 12-scenario synthetic results are preserved in evidence/experiments.json and raw-experiments.json. Historical manual real-DB/API failure observations remain in POSTMORTEM.md and original screenshots. Neither supplies exact v2 automatic restart timings.

New local native verification exercises the Bash health/smoke scripts against a real child FastAPI process with file-backed SQLite. These are functional checks, not a PostgreSQL or Docker benchmark. CI is configured to produce separate real Docker crash, manual DB and manual API outage observer JSON files. Exact measurements may be quoted only after those artifacts are collected and inspected. Until then, automatic recovery timing and new Docker outage timing are NOT VERIFIED.

The observer records UTC events, first health failure, first Prometheus failure, observed alert firing and resolution, restart count and new readiness. It distinguishes missing/not-applicable values with null. Continuous request measurements include total/successful/failed counts, error percentage and nearest-rank p50/p95 for the bounded interval. See FAULT_INJECTION.md for timing definitions and polling limitations.

No performance improvement, production uptime, universal zero downtime or cloud savings is claimed. Small synthetic local runs do not establish monthly availability. Do not compare the old 3-second local detector times directly with the real 30-second Prometheus alert hold.

## Blue-green deployment decision

Deferred rather than labeling an untested change as zero downtime. The current API has per-process SLIs and an in-process incident writer; running two writers against the same incident table could create duplicate incidents, and the current proxy does not provide readiness-based routing or drain control. With no local Docker runtime available, those behaviors cannot be safely verified here before adding topology complexity.

A future scoped experiment should coordinate or externalize incident evaluation, run independent blue/green API instances, probe readiness before routing, atomically switch a reverse proxy, drain old connections, and use continuous synthetic registration/read traffic. Record total/success/failure counts, p50/p95, deployment start/end and failed-request timestamps. Say only “Zero failed requests observed during the measured local deployment experiment” if the measured result supports it. Do not claim that experiment has been implemented or run in v2.
