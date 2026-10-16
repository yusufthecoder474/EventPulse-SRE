# Cvent-targeted resume evidence

Use these claims only after studying the code and explaining the work accurately. Local verification used SQLite; PostgreSQL integration and remote CI remain pending. Do not imply independent manual authorship or production deployment if that is not your experience.

## Exactly three resume bullets (XYZ format)

- Achieved detection of 8/8 labeled user-impact scenarios with zero alerts across four baseline/noise scenarios by instrumenting a FastAPI event service with Prometheus metrics, rolling SLIs and deduplicated incident tracking across 12 local HTTP experiments.
- Validated registration and failure-handling behavior through 34 passing backend tests by testing atomic capacity updates, idempotent requests, rollback, readiness probes, metric correctness and token-protected fault injection in a local SQLite environment.
- Delivered a six-page React/TypeScript reliability console with two passing desktop/mobile browser flows by integrating live request telemetry, latency charts, incident evidence, SLO calculations and exportable experiment results.

## Evidence mapping

| Claim | Supporting artifact | Boundary |
|---|---|---|
| 8/8 detections; zero false alerts; 12 experiments | evidence/experiments.json, raw-experiments.json, scripts/evaluate.py | scenario-level, local detector, synthetic faults |
| 34 backend passes | evidence/backend-junit.xml, backend-tests.txt, backend/tests/ | one PostgreSQL integration test skipped |
| Six pages; two browser flows | frontend/src/App.tsx, evidence/browser-junit.xml, docs/screenshots/ | Vite-served real UI, local API; no deployment claim |

## Additional measured details for discussion

Observed 3,060 affected-window GET /events requests across all scenarios, excluding recovery traffic. Median first-incident detection 1.753s and median incident resolution after clearing 3.018s under a **3-second** window and 500ms evaluator interval. Precision and recall each 100% in this small synthetic set; Wilson 95% interval each 67.56%–100%. Describe the sample size whenever discussing accuracy. All scenario recovery probes succeeded; these numbers do not establish production reliability.

## 60-second project explanation

“EventPulse is a small event-registration service that I use to demonstrate reliability engineering. The backend checks event capacity and prevents duplicate registrations. I added request counters, latency histograms, database readiness checks and structured logs with correlation IDs. The React console shows request-based availability, tail latency, error budgets and incident evidence. There are two detection paths: a short-window local detector for demonstrations, and separately configured Prometheus rules with Alertmanager grouping. In a protected local lab, I can introduce slow responses, server errors and simulated dependency failures, then check recovery using fresh requests. I ran 12 synthetic HTTP experiments, including six held-out scenarios; all eight expected impact scenarios were detected with no alerts in the four baseline or noise cases. I also verified 34 backend tests and two browser flows. Local verification used SQLite; PostgreSQL, Docker runtime and remote CI still require validation.”

## Architecture interview questions and answer anchors

1. **How does registration prevent overselling?** Conditional database UPDATE locks the event row and checks remaining capacity; insertion occurs in the same transaction. Rejections and uniqueness conflicts roll back the increment.
2. **Why use an idempotency key?** A retried POST can return the original registration without reserving another seat. Reusing the key with a changed body is a 409 conflict.
3. **Why PostgreSQL and why a SQLite fallback?** PostgreSQL is the intended Compose datastore. SQLite enables local checks without infrastructure; it cannot substitute for testing PostgreSQL locking and deployment.
4. **What is request flow?** React/Vite or nginx proxy -> middleware -> FastAPI handler -> SQLAlchemy transaction -> response; middleware records status/duration and returns a correlation header.
5. **What survives a restart?** Database registrations and incident records. In-memory rolling samples, pending detector state and fault settings reset. Prometheus history persists in its separate volume.
6. **How do you control metric cardinality?** Route templates, normalized method and status only; no registration IDs, emails, query strings or correlation IDs in labels.
7. **What happens during a real database outage?** Readiness/business requests fail and incident persistence may also fail. Prometheus remains a separate observation plane. The lab's database button is a simulation.
8. **What would change for multiple replicas?** Durable shared incident coordination, out-of-process detection, aggregated counter queries and authenticated operations access. Current console supports one worker only.

## SRE interview questions and answer anchors

1. **SLI versus SLO versus SLA?** Measured indicator, chosen reliability objective, and contractual commitment respectively. This project has educational SLOs, not a customer SLA.
2. **How is availability defined?** Non-5xx business responses divided by all business responses within an explicit window; no data is unknown. Explain that 4xx is treated as available, not a completed booking.
3. **What does a 2x burn rate mean?** Errors consume allowed budget at twice its permitted ratio. Remaining budget may be negative.
4. **Why p95 rather than mean alone?** Tail latency exposes slow experiences hidden by an average. Prometheus estimates histogram quantiles; console uses exact nearest-rank samples.
5. **How are false alerts measured?** At scenario level against labels chosen before running, including warning noise with no user impact. Zero observed false positives in four cases does not prove a zero production false-positive rate.
6. **Why separate development and held-out cases?** To avoid tuning thresholds against all scenarios. The held-out parameters are predefined and not used to change thresholds.
7. **How do alerts deduplicate?** Local incidents group by active signal; Alertmanager independently groups Prometheus alerts by alertname and service.
8. **How is recovery verified?** Clear mitigation/fault, wait for the observation window and confirm fresh successful probes. No traffic clearing a predicate is insufficient.
9. **Why two alert policies?** A short-window detector makes local rehearsals demonstrable. Longer Prometheus windows reduce noise; their timing was not validated by the short-window harness.
10. **What is the strongest limitation?** Synthetic single-host tests with a small sample, simulated dependency faults and pending PostgreSQL/runtime CI verification. Explain next tests before claiming stronger reliability.

Intended repository: https://github.com/yusufthecoder474/EventPulse-SRE — publication blocked in this environment; no remote commit is claimed. See TEST_RESULTS.md and PUBLISH_GITHUB.ps1.
