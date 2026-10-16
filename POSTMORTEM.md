# EventPulse-SRE — Blameless Postmortem

**Status:** Controlled local fault-injection experiment — completed; documentation review pending.

**Incident ID:** EP-LOCAL-20261016-01

**Date:** October 16, 2026

**Severity:** Local testing only. The `EventPulseTargetUnreachable` alert carried the SEV2 label, but no production incident occurred.

**Environment:** Docker Compose, FastAPI, PostgreSQL, Prometheus, Alertmanager and Grafana.

**Author:** Project maintainer

**Reviewers:** Not yet assigned

**Timezone:** IST (UTC+05:30)

**Observation window:** Local monitoring through Prometheus and Grafana. Grafana screenshots used a 30-minute rolling window. Exact scrape and alert evaluation intervals require confirmation from configuration.

## 1. Incident Summary

Two controlled fault-injection experiments were conducted to evaluate the EventPulse-SRE platform's ability to detect service failures, expose useful telemetry and recover after restoration.

The first experiment intentionally stopped the PostgreSQL container to evaluate database-dependent API behavior.

The second intentionally stopped the application API container to verify Prometheus target monitoring and alert delivery to Alertmanager.

Both experiments were performed in a local development environment using synthetic data. No production customers, infrastructure or live event attendees were affected.

## 2. Impact

### Experiment A — PostgreSQL Outage

**Fault:** PostgreSQL container intentionally stopped.

**Observed behavior:**

- Database readiness endpoint returned HTTP 503.
- Response body: `{"database_ready":false}`.
- `GET /events` returned HTTP 503.
- Error response: `{"error":"Database unavailable"}`.
- Prometheus database-readiness metric reported 0.
- After PostgreSQL was restarted, `GET /events` returned HTTP 200.
- The readiness endpoint subsequently returned HTTP 200 with `{"database_ready":true}`.
- Prometheus database-readiness metric returned to 1.

**Impact:** Database-dependent operations were unavailable during the controlled outage. No actual customer impact occurred.

### Experiment B — API Outage

**Fault:** FastAPI container intentionally stopped.

**Observed behavior:**

- Prometheus query `up{job="eventpulse"}` returned 0.
- `EventPulseTargetUnreachable` entered the FIRING state.
- Alertmanager displayed the alert through the `local-console` receiver.
- The API container was restarted.
- After startup, the readiness endpoint returned HTTP 200.
- Prometheus query `up{job="eventpulse"}` returned 1.
- The alert subsequently became inactive.
- Alertmanager displayed no active alert groups.

**Impact:** The API monitoring target was temporarily unreachable. This was an intentional local test, not a production outage.

### Measurement Limitations

The available screenshots do not establish the complete request denominator, total failed requests, exact incident duration or alert detection latency.

Healthy-period Grafana screenshots showed request throughput, availability and latency metrics, but these values should not be interpreted as complete outage performance measurements.

No production downtime, financial impact or customer-facing service-level breach is claimed.

## 3. Timeline

The timestamps below are taken from the available HTTP responses and monitoring evidence. They represent observed events rather than a complete second-by-second fault schedule.

| Timestamp (IST) | Observation or action | Evidence |
|---|---|---|
| Oct 16, 22:07:07 | PostgreSQL outage observed; readiness returned HTTP 503 | PowerShell HTTP response |
| Oct 16, 22:07:26 | `GET /events` returned HTTP 503 | PowerShell HTTP response |
| Oct 16, 22:08:34 | `GET /events` returned HTTP 200 following database restart | PowerShell HTTP response |
| Oct 16, 22:10:12 | Readiness returned HTTP 200; database ready | PowerShell HTTP response |
| Oct 16, approximately 22:12 | API shutdown experiment; Prometheus target became unreachable | Prometheus screenshots |
| Oct 16, 22:12:26 | Alertmanager evidence displayed the target-unreachable alert | Alertmanager screenshot |
| Oct 16, 22:14:37 | Fresh readiness probe returned HTTP 200 after API restart | PowerShell HTTP response |
| After recovery | Prometheus reported `up=1`; alert rules inactive; Alertmanager showed no active groups | Recovery screenshots |

The exact initial API shutdown time, first alert evaluation time and alert-resolution time were not independently recorded.

## 4. Contributing Factors

### Confirmed

1. PostgreSQL was an essential dependency for database-backed endpoints.
2. Stopping PostgreSQL caused the readiness endpoint and event-listing endpoint to return HTTP 503.
3. Stopping the API made its Prometheus metrics endpoint unreachable.
4. Prometheus and Alertmanager detected and displayed the API target failure.
5. API startup was not instantaneous; an early request after restart returned an empty response before later health checks succeeded.

### Not Established

- Whether automated recovery or retry logic would have restored service without manual intervention.
- Exact time-to-detection and time-to-recovery.
- How alert routing would behave in a real production notification environment.
- Whether the same results would occur under sustained concurrent traffic.

The failures were deliberately introduced and were not attributed to individual error.

## 5. Detection and Response

**Detection mechanisms:**

- Prometheus target-health metric `up{job="eventpulse"}`.
- Database-readiness metric `eventpulse_database_ready`.
- Prometheus alert rule `EventPulseTargetUnreachable`.
- Alertmanager alert grouping and local-console receiver.
- Grafana application and infrastructure monitoring panels.

**Response performed:**

The operator manually restarted the affected Docker Compose services and checked their health.

Recovery was confirmed using fresh HTTP requests, Prometheus metrics and alert-state inspection.

For the API outage, recovery was supported by the return of `up=1`, an HTTP 200 readiness response and the absence of active target-unreachable alerts.

For the database outage, recovery was supported by HTTP 200 responses and `eventpulse_database_ready=1`.

An inactive alert alone would not establish service recovery; fresh successful probes provided additional verification.

## 6. Corrective and Follow-up Actions

| Action | Owner | Target date | Verification |
|---|---|---|---|
| Preserve outage and recovery screenshots | Project maintainer | Oct 18, 2026 (proposed) | Evidence files checked |
| Review Prometheus recording and alert rules | Project maintainer | Oct 18, 2026 (proposed) | Configuration inspection |
| Verify alert routing and notification behavior | Project maintainer | Oct 20, 2026 (proposed) | Repeatable local notification test |
| Record exact timestamps in future experiments | Project maintainer | Oct 20, 2026 (proposed) | Timestamped test log |
| Evaluate recovery under sustained synthetic traffic | Project maintainer | Oct 20, 2026 (proposed) | Reproducible experiment report |

Dates are proposed follow-up targets, not confirmed commitments.

## 7. Lessons Learned

**What worked:**

- Prometheus detected the unreachable API target.
- Alertmanager displayed the active alert.
- PostgreSQL readiness checks reflected dependency failure.
- Database-backed endpoints returned HTTP 503 during the outage.
- Fresh probes confirmed service restoration.
- Grafana visualized application and infrastructure metrics.

**What could improve:**

- Capture precise fault-start and recovery timestamps automatically.
- Preserve before, during and after screenshots for every experiment.
- Record request totals and error counts during outages.
- Distinguish alert resolution caused by successful recovery from resolution caused by missing traffic.
- Validate alert routing beyond the local-console receiver.

## 8. Evidence

Evidence from the controlled local fault-injection experiments is stored in `docs/screenshots/`.

### PostgreSQL Outage and Recovery

- `postgresql-outage-503.jpeg` — HTTP 503 readiness response when PostgreSQL was stopped.
- `postgresql-recovery-200.jpeg` — HTTP 200 readiness response after PostgreSQL recovery.

### Prometheus Monitoring and Alerts

- `prometheus-target-unreachable-firing.jpeg` — Target-unreachable alert in the FIRING state.
- `prometheus-target-recovered.jpeg` — Prometheus query showing target recovery.
- `prometheus-target-health.jpeg` — Prometheus target-health page showing the API target UP.
- `prometheus-alerts-resolved.jpeg` — Prometheus alert rules in the inactive state.

### Alertmanager

- `alertmanager-resolved.jpeg` — Alertmanager showing no active alert groups after recovery.

The active Alertmanager alert was observed during testing, but a separately saved active-alert screenshot is not currently included in the evidence directory.

### Grafana Monitoring

- `grafana-live-metrics.jpeg` — Application and infrastructure telemetry visualized in Grafana.
- `grafana-dashboard-healthy.jpeg` — Grafana dashboard after service recovery.

These screenshots document controlled local experiments. They do not establish production availability, automatic recovery or complete incident-duration measurements.

## 9. Conclusion

The EventPulse-SRE local experiments demonstrated that the monitoring stack could detect an API target failure, expose database-readiness changes, display alerts and provide evidence of recovery after manual intervention.

These results support the project's demonstration of observability, controlled fault injection and operational troubleshooting.

The experiments do not establish production reliability, automatic self-healing, guaranteed service availability or quantified business savings.

**Final classification:** Controlled local reliability experiment, not a real production incident.