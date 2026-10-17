# v2 operational runbook

Run Bash from Linux/WSL at the repository root. Existing Windows commands remain in SETUP_WINDOWS.md. The original root INCIDENT_RUNBOOK.md remains useful for application-level investigation.

| Script | Real operation | Requirements / failure behavior |
|---|---|---|
| scripts/health-check.sh | Checks live and ready HTTP status | curl; rejects non-loopback URLs; non-200/transport failure exits nonzero |
| scripts/smoke-test.sh | Real synthetic registration, idempotent replay, retrieval, metrics | Python + curl; rejects errors and assertions |
| scripts/verify-stack.sh | Compose config, running state for six services, API + monitoring health | Docker Compose + Python; exits on failure |
| scripts/collect-diagnostics.sh | Bounded container state + readiness observations | Never exports environment, raw logs, resolved config, credentials or attendees |
| scripts/deploy-local.sh | Build, in-place deployment, wait and smoke | Explicit local-host approval env; reviewed full SHA; clean working tree |
| scripts/reliability.py | Independent fault/health/Prometheus/alert/recovery timestamps | Explicit local fault flag and isolated project name |

All scripts use Bash safety settings, dependency checks and meaningful exit codes. `lib.sh` shares root resolution and helpers. No backup/restore script was added because a safe round-trip restore was not verified; a script that merely creates a dump would not establish restorability.

```bash
python scripts/bootstrap.py
export COMPOSE_PROJECT_NAME=eventpulse-v2-demo
docker compose up --build -d --wait --wait-timeout 180
bash scripts/verify-stack.sh
OUT_DIR=evidence/v2/diagnostics bash scripts/collect-diagnostics.sh
```

Wait for at least two Prometheus scrapes before `verify-stack.sh`. If an alert is absent, inspect request volume and scrape health before assuming a healthy service. Use `docker compose ps`, select individual relevant JSON logs locally and correlate X-Request-ID; do not paste credentials into notes. Health failures while the process remains alive require investigation; Docker health checks do not trigger restarts.

To test persistence in a disposable local stack: run smoke, recreate db and api without deleting volumes, rerun with `SMOKE_EXPECT_EXISTING=true`. The assertion requires replay HTTP 200, not a silently recreated HTTP 201. Never use `docker compose down -v` on data you need.

Safe update on an approved host: check out the reviewed commit, export `REVISION=$(git rev-parse HEAD)` and `DEPLOY_LOCAL_APPROVED=yes`, then `bash scripts/deploy-local.sh`. This is an in-place release and may interrupt requests. Rollback requires checking out a reviewed previous SHA and rerunning; database-schema rollback is not automated. No remote deployment target or credential is configured in GitHub Actions.
