# Reliability and performance report — v2

Verified code: `1b98638c7f4cd289434d0cf49b5e3f8e5e1f522a`. CI: https://github.com/yusufthecoder474/EventPulse-SRE/actions/runs/38998784660. One independently observed trial per scenario in this PR run. Other workflow invocations are not double-counted.

| Scenario | Recovery mechanism | Requests | Failed | p50 (ms) | p95 (ms) |
|---|---|---:|---:|---:|---:|
| api-crash | automatic Docker restart | 24 | 12 | 16.307 | 24.593 |
| database-outage | manual start | 179 | 159 | 23.594 | 42.955 |
| api-outage | manual start | 820 | 732 | 12.493 | 28.145 |

| Scenario | Health detection (s) | Prometheus detection (s) | Alert firing (s) | Restoration (s) | Alert resolution after readiness (s) |
|---|---:|---:|---:|---:|---:|
| api-crash | 0.121 | 0.761 | not observed / N/A | 0.832 | not observed / N/A |
| database-outage | 0.118 | 3.992 | not observed / N/A | 0.317 | not observed / N/A |
| api-outage | 0.262 | 4.258 | 38.773 | 1.296 | 5.243 |

Health/scrape/alert detection intervals start at the fault-command request. For the crash, restoration is **Docker die event -> fresh successful readiness** (0.832464s; restart count 0 -> 1). For manual scenarios, restoration is **explicit start action -> fresh successful readiness**, excluding intentional hold time. These intervals are not interchangeable. The API outage alert fired after 38.772743s and resolved 5.243070s after observed readiness; its configured hold is 30s plus scrape/evaluation/observation delay.

The abrupt crash produced 12 failed requests out of 24 observations; no zero-failure recovery is claimed. The manual DB outage produced 159 failures of 179 requests, and the manual API outage produced 732 failures of 820 requests. API-crash alert timestamps are null because the incident did not persist through the alert hold. A null field is not a zero-second measurement.

Exact UTC timestamps and request denominators are in evidence/v2/ci-*-summary.json. Raw request samples/events and screenshots are in the linked Actions artifact. Polling target is 100ms but requests and Docker inspection consume time. The observer uses host UTC wall clock for event intervals; sampling/clock skew limits precision. Request durations use a monotonic clock and quantiles use nearest rank, including failed requests. Fast connection errors can have short durations, so these p95 values are not healthy-only experience measures.

No confidence interval or general accuracy claim is made from n=1 per scenario. These are bounded functional reliability trials, not maximum-throughput tests, production SLAs, monthly availability or measured business savings.

## Failed attempts retained

The first crash test did not terminate PID 1 and failed the restart-counter assertion; see ci-initial-failure-summary.json. It is excluded from successful recovery measurements. The corrected hook is disabled by default, local/POSIX only, and requires explicit Compose opt-in; it adds no HTTP endpoint.

An optional native Locust attempt requested five users and ten seconds but terminated early (exit 2) when psutil could not locate its CPU-monitor PID in the restricted local environment. Eighteen partial requests succeeded, but that run is a **FAIL** and supplies no successful throughput/latency benchmark. See evidence/v2/native-locust-attempt.json. No dependency was patched to conceal the failure.

Historical twelve-scenario in-process detector experiments and the maintainer's manual outage screenshots/postmortem are preserved unchanged. They are distinct from these three new Docker observer trials.

## Reproduction

Use the isolated eventpulse-v2-demo project and explicit crash-hook opt-in described in docs/FAULT_INJECTION.md. The observer refuses unexpected project names, non-loopback targets and evidence overwrite. Docker/Compose and a local disposable stack are required; no AWS account is involved.

## Blue-green decision

Deferred to preserve correctness. The current API has per-process telemetry and an in-process incident writer; two writers sharing one database need coordination to avoid duplicate incidents. The existing proxy has no readiness-aware switch/drain mechanism. No untested proxy topology was added just to claim zero downtime.

Future experiment: coordinate or externalize incident evaluation, run independent blue/green API instances, verify readiness before routing, atomically switch a reverse proxy, drain old connections, and send continuous synthetic read/registration traffic. Record requests, failures, p50/p95 and deployment start/end. Only say “Zero failed requests observed during the measured local deployment experiment” if that measured result supports it. That experiment has not been implemented or run in v2.
