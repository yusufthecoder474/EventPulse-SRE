# SLI and SLO definitions

Business scope: requests routed to GET /events, POST /registrations, GET /registrations/{registration_id}. Health, metrics, operations polling and unmatched paths do not enter the denominator. All outcomes are responses; <500 is treated as available. A 409 full event is an expected business rejection, not server unavailability. Registration completion metrics separately identify failures, including rejected inputs.

| Quantity | Formula |
|---|---|
| Availability SLI | 1 - HTTP 5xx responses / business responses |
| Availability target | 99% over the explicit rolling measurement window |
| Latency SLI | responses taking <=500ms / business responses |
| Latency target | at least 95% within 500ms |
| RPS | business responses / full window duration |
| Remaining availability budget | 1 - observed error ratio / 0.01 |
| Burn rate | observed error ratio / 0.01 |

Negative remaining budget means exhausted beyond allowance. The overview ring clips its display to 0..100%; SLO Dashboard retains the negative value. No responses returns null SLIs and quantiles. New process startup uses the full configured window as the RPS denominator; early RPS is therefore conservative. These are rolling request objectives, not monthly contractual uptime guarantees.

Default console window: 60s, configurable 2..3600s. Automated experiments explicitly shorten it to 3s to make local rehearsals fast; their times do not predict production alert timing. Each console chart divides the current window into twenty bins. Nearest-rank p50/p95/p99 use actual observed response durations.

Local detector: minimum 5 business responses, error ratio >5% or p95 >500ms, sustained >=1s, sampled every 500ms. Availability incidents SEV2, latency incidents SEV3. No-data clears the local predicate but does not establish recovery. Recovery evidence must include fresh successful probes.

Prometheus availability fast burn: 5m AND 1h burn >14.4x, >=100 requests in 5m, for 2m. Latency alert: 5m p95 >500ms, >=100 requests in 5m, for 2m. API scrape unreachable alert after 30s covers missing request telemetry. No-data ratios remain unknown and cannot be mistaken for healthy values. The long-window alerts are configured separately and were not benchmarked by the short-window experiment harness.
