# v2 audit — baseline 0a6efd1 (2026-10-17)

Source: clean clone of the existing main branch, commit `0a6efd1c09ff30cdb0ff838da7d79ba858582e10`. The supplied attachment contains instructions, not a project ZIP. The remote matches the specified baseline and is used as the authoritative source. Existing frontend, APIs, registration transactions, screenshots, experiment outputs and POSTMORTEM.md are preserved.

| Feature | Current status | Evidence | Required improvement | Priority |
|---|---|---|---|---|
| FastAPI registration, validation, idempotency and capacity transactions | Implemented; historical tests and successful remote CI | backend/app, evidence/backend-junit.xml; CI run 38942106723 | Run regression; retain behavior | P1 |
| PostgreSQL + Docker stack | Implemented; maintainer's manual outage evidence; CI success | compose.yml, POSTMORTEM.md, screenshots; baseline Actions | Add stack smoke and persistence check to CI | P1 |
| Six-page React frontend | Implemented; prior unit/browser evidence | frontend/src; evidence/browser-junit.xml | Preserve UI and contracts | P1 |
| Request counters and latency histograms | Implemented, low-cardinality templates | backend/app/telemetry.py | Initialize zero-error series before first failure; test healthy PromQL | P1 |
| Prometheus SLIs | Configured; target/DB failure screenshot evidence | monitoring/alerts.yml, screenshots | Fix sparse new-5xx-series ratio; explicit no-traffic guards; expand p50/SLO/budget panels | P1 |
| Local incident detector and fault TTL | Implemented; independent short-window experiments | scripts/evaluate.py, evidence/experiments.json | Preserve; distinguish local detector and Prometheus timestamps | P1 |
| Grafana | Provisioned and maintainer screenshots | monitoring/grafana; docs/screenshots | Add success/error/SLO/budget/target/p50 panels | P1 |
| Alertmanager | Configured local receiver; historical resolved screenshot | monitoring/alertmanager.yml; POSTMORTEM.md | Validate config in CI; no external delivery claim | P1 |
| GitHub Actions | Actual SUCCESS at baseline | https://github.com/yusufthecoder474/EventPulse-SRE/actions/runs/38942106723 | Add ShellCheck, Compose validation, full-stack smoke, recovery experiment | P1 |
| Bash automation | Missing | scripts contains Python and PowerShell only | Health, smoke, verify, sanitized diagnostics and deployment scripts | P1 |
| Experiment timestamps | Incomplete for real outages | POSTMORTEM.md explicitly states limitations | Observer logs UTC events separately for health, Prometheus and alerts | P1 |
| Automated restart | Missing restart policy; manual recovery only | compose.yml, POSTMORTEM.md | Process-crash restart policy plus measured CI trial | P2 |
| Database persistence | Named volume configured | compose.yml | Registration survives API recreation; keep destructive volume operations out of tests | P2 |
| Deployment automation | No target; build CI exists | existing workflow | Local transactional release script; AWS target pending approval | P2 |
| Blue-green / zero-failure deployment | Absent; console telemetry per process | architecture and telemetry.py | Document scoped future experiment; avoid breaking incident state | P3 |
| AWS | Not deployed | no cloud infrastructure files | EC2 + Compose preparation; zero inbound app/admin ports; SSM tunnel | P4 |
| Secrets and exposure | .env ignored; loopback ports; local-only fault token | .gitignore, compose.yml, backend/app/main.py | Preserve; never collect resolved Compose env in diagnostics | P1 |
| Publishing script | Obsolete: creates a new repo and rejects existing repo | PUBLISH_GITHUB.ps1 | Replace with existing-repo feature branch instructions | P1 |
| Historical documentation | Some original files still say remote CI unpublished | TEST_RESULTS.md, RESUME_EVIDENCE.md | Preserve as dated history; link current v2 verification report | P1 |

No measured latency reduction, automatic recovery, zero-failure rollout or AWS deployment is established by this audit. Baseline CI success is distinct from the new workflow's eventual result.
