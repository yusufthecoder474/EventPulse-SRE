# SLI/SLO definitions and v2 PromQL

The existing local demonstration objective stays **99% non-5xx business responses**, with **95% of responses <=500ms**. Changing only a label to 99.9% would make the frontend, local detector and existing budget math inconsistent. These educational targets are not Cvent policy or monthly contractual availability.

| Signal | Query / definition |
|---|---|
| Throughput | eventpulse:business_requests:rate5m |
| Server error ratio | eventpulse:business_errors:ratio5m |
| Request success ratio | eventpulse:business_success:ratio5m |
| p50 / p95 | histogram_quantile(0.5 or 0.95, sum by(le)(rate(eventpulse_http_duration_seconds_bucket{route=~"/events|/registrations.*"}[5m]))) |
| Target availability | avg_over_time(up{job="eventpulse"}[5m]) |
| Database readiness | eventpulse_database_ready |
| Latency compliance | eventpulse:business_latency:ratio5m |
| Remaining availability budget | 1 - error_ratio / 0.01 |
| Consumed availability budget | error_ratio / 0.01 |
| Availability compliance | success_ratio >= bool 0.99 |

`monitoring/alerts.yml` contains exact executable formulas. Ratios are filtered by denominator >0. Thus no requests produce an absent time series (unknown), not 100% health or 0% errors. Error counters initialize zero 500/503/504 series for all three business templates so the first failing scrape has a prior sample for rate(). The fallback `or vector(0)` alone cannot reconstruct a missing counter's pre-error sample. Low-volume ratios are visible, but impact alerts require >=100 requests over 5m. Two scrapes and enough traffic are needed for rate-based values.

Target availability samples scraper reachability; it is distinct from successful business responses and from readiness. Missing samples/removed targets are not assumed healthy and there is no permanent expected-target inventory. All no-data gaps must remain visible. Histograms are bucket-interpolated, unlike exact nearest-rank console quantiles. Counter reset handling uses rate() rather than subtracting raw counters.

Grafana has 15 real-metric panels; no random history is generated. The original root SLI_SLO.md explains the 60s console window, shortened 3s synthetic experiment window and burn alert thresholds. `monitoring/rules.test.yml` checks no traffic, healthy traffic and target-down firing/resolution using promtool in CI. It does not prove production detection accuracy.
