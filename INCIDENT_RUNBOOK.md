# Incident runbook

## Lifecycle

Normal -> pending impact -> firing -> investigate -> mitigate -> verify recovery -> resolved and review. The local detector groups active incidents by signal. Repeated requests update telemetry without creating duplicate active records. Automated resolution means predicate cleared; confirm recovery with new probes before declaring service restored.

## Elevated errors / SEV2

1. Check the observation window, volume gate, 5xx ratio and stale-data banner. Exclude expected 4xx business rejections from server availability counts.
2. Open affected endpoint metrics and incident evidence. Copy a correlation ID from response headers and locate the corresponding JSON request log. Do not copy tokens or attendee addresses into notes.
3. Check database readiness and real database logs. A simulated database fault reports false readiness even while PostgreSQL is running. Determine which applies before acting.
4. Inspect the local fault state. Clear an injected fault using authorized lab controls; for a real stopped PostgreSQL dependency, restart only that local service with `docker compose start db`.
5. Send fresh requests and inspect HTTP status, latency and readiness. Wait for the affected window to age out; document the first successful probe and incident end.
6. Record impact, hypothesis, action and evidence in notes, then complete POSTMORTEM.md.

## High latency / SEV3

Check p50 vs p95/p99 and histogram shape; avoid assuming average latency represents tail experience. Check endpoints and dependency readiness. In this simulator a latency or dependency fault deliberately adds delay. In a real service investigate query latency, pool wait and downstream deadlines before choosing mitigation. Clear the local delay and verify fresh latency samples. A dependency timeout can trigger both availability and latency; that is two signal groups for one underlying cause.

## Missing telemetry

A dead API cannot report requests. Check the independent Prometheus `up` signal and TargetUnreachable alert. Local in-process incident detection cannot observe its own process being stopped or persist through a real failed database. Never interpret an empty chart as recovered. When no business traffic exists, availability is unknown.

## Alert delivery

Prometheus /alerts and Alertmanager show configured longer-window alerts. The receiver is intentionally local with no notification integration. Do not expect email, Slack, or automatic Incident Center ingestion. Inspect rule and scrape health separately from application fault controls.
