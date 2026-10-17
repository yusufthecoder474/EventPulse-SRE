# v2 changelog

- Reused the exact existing main baseline 0a6efd1, preserving frontend/API/database contracts and historical evidence.
- Added Bash health, smoke, stack verification, sanitized diagnostics and opt-in in-place deployment tools with syntax/ShellCheck and real HTTP tests.
- Initialized server-error counter series, added explicit no-traffic guards, success/latency recording rules, promtool test cases and seven Grafana panels (15 total).
- Added unless-stopped policies and graceful shutdown settings without claiming that health checks restart containers.
- Added bounded, isolated local Compose crash/manual-outage observation with distinct UTC events and request latency/error measurements.
- Strengthened CI with full-stack validation, persistence checks, real recovery experiments and new artifact paths.
- Added optional EC2/SSM/Compose preparation with no inbound ports, encrypted storage and explicit billing approval boundary.
- Replaced obsolete new-repository publishing behavior; feature-branch/PR update only.
- Deferred unverified blue-green topology and backup/restore; no fabricated cloud, timing or performance claims.

- Corrected the ineffective PID-namespace SIGKILL experiment using an explicitly enabled local SIGUSR1 abrupt-exit hook; preserved the failed trial.
- Verified all expanded CI steps, 50 backend tests, 3 frontend tests, 2 browser flows and three real Docker observer scenarios at implementation SHA 1b98638.
- Recorded a single measured 0.832464s crash restoration interval and its 12 failed requests; no zero-downtime claim.
