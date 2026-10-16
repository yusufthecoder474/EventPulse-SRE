# Monitoring

| Signal | Metric / source | Notes |
|---|---|---|
| Completed requests | eventpulse_http_requests_total | method, route template, status |
| Duration | eventpulse_http_duration_seconds | cumulative buckets 10ms..5s plus +Inf |
| Registration attempts | eventpulse_registrations_total | success, replayed, failure; includes validation and injected faults |
| Readiness | eventpulse_database_ready | SELECT 1; simulated database fault overrides zero |
| In flight | eventpulse_inflight | Gauge decremented in finally |
| Uptime | eventpulse_uptime_seconds | wall-clock process uptime |
| Version | eventpulse_service_info | fixed version label |
| OS resources | process_resident_memory_bytes / process_cpu_seconds_total | Python client process collector; OS support varies |

RPS and 5xx rate are derived from counters. Quantiles are derived from the histogram in Prometheus, and exact sampled durations in the console. Do not average quantiles across instances. Low-cardinality route templates avoid per-user series. The metrics endpoint and operations polling are counted in HTTP metrics but excluded from business SLIs and alert ratios.

Provisioning files automatically load Grafana datasource and eight panels. Prometheus scrapes every 5s. Alertmanager groups by alertname and service, waits 10s, repeats at 1h. No webhook, email or external notification is configured. View alert states in Prometheus /alerts and Alertmanager UI. Local Incident Center is a separate shorter-window detector and does not consume Prometheus alerts.

Prometheus alert syntax validation is configured in CI via promtool. Runtime container and scrape validation must be reported separately from file creation. For a native API monitored by Docker, update the scrape target locally to `host.docker.internal:8000` on Docker Desktop and bind the API appropriately only after considering the local demo boundary; native local testing defaults to loopback and does not require Prometheus.

References: https://prometheus.io/docs/practices/histograms/ and https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/ .
