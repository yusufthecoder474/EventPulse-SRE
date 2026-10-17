# v2 final verification report — 17 October 2026

Source baseline: `0a6efd1c09ff30cdb0ff838da7d79ba858582e10`. No project ZIP accompanied the instructions; a clean clone of the specified existing repository supplied the current source. Original POSTMORTEM.md, screenshots and all 24 historical evidence files remain unchanged.

**Verified implementation SHA:** `1b98638c7f4cd289434d0cf49b5e3f8e5e1f522a`  
**Successful CI:** https://github.com/yusufthecoder474/EventPulse-SRE/actions/runs/38998784660  
**Job:** 117297090414  
**Artifact:** 12088202136 — sha256:ef44dd8d3b5ab54070d8f8a0aadd267a2aff066a341c2782af99507735913a81  
**Pull request:** https://github.com/yusufthecoder474/EventPulse-SRE/pull/1

Documentation/evidence may be committed after the tested implementation; the SHA above is the exact runtime implementation that passed. Do not silently attribute this run to a different SHA.

| Capability | Status | Evidence / boundary |
|---|---|---|
| Local initial Python tests | PASS: 46 passed, 1 skipped | evidence/v2/backend-tests.txt and backend-junit.xml before the later crash-hook correction |
| Final CI Python tests | PASS: 50 passed, no skipped test | Includes PostgreSQL concurrency/rollback integration and guarded crash-hook tests |
| Frontend unit tests / typecheck / build | PASS: 3 tests + build | Completed CI step and artifact |
| Desktop/mobile browser flows | PASS: 2 | Real Vite UI against the Compose PostgreSQL-backed API; screenshots/JUnit in artifact |
| Bash syntax / ShellCheck / credential-pattern scan | PASS | CI static step |
| Bash health / registration smoke | PASS | Real native-process tests and Compose integration |
| Six-service Docker stack / images | PASS | CI build, start and wait |
| Database registration persistence | PASS | Recreate DB and API without deleting volumes; replay must return 200 |
| Prometheus rules/config and three rule-test scenarios | PASS | promtool check config/rules and test rules |
| Alertmanager configuration | PASS | amtool check-config |
| Prometheus target/rules, Grafana health, Alertmanager status | PASS | Executed verify-stack.sh / verify_monitoring.py |
| Grafana dashboard | PASS: 15 panels structurally checked; health endpoint ready | Per-panel visual rendering and the new Grafana dashboard screenshot are not separately verified |
| Docker API process crash recovery | PASS: one measured PR-run trial | RestartCount 0 -> 1, die event, fresh ready 200; 0.832464s interval; 12 failed of 24 requests |
| Manual DB outage / recovery | PASS | Separate observer JSON; explicit stop/start, not automated DB recovery |
| Manual API outage / alert / recovery | PASS | Distinct health, scrape, firing, start, readiness and resolution observations |
| In-place deployment helper | NOT RUN | Script is opt-in and reviewed; CI executes its core Compose operations but not this helper end-to-end |
| Optional native Locust attempt | FAIL | psutil CPU-monitor cannot find its PID in this restricted local environment; partial results excluded |
| Actual delayed-DB response injection | NOT VERIFIED | No network shaping or destructive query workload added |
| Blue-green deployment | NOT RUN / deferred | Plan in PERFORMANCE_REPORT.md; no zero-downtime claim |
| Backup / restore round trip | NOT RUN | No unverified backup script added |
| AWS template static properties | PASS | YAML parsing, no ingress, IMDSv2 and encrypted EBS assertions; AWS API validation NOT RUN |
| Actual AWS deployment | NOT VERIFIED | No AWS credentials requested, billable resources created or deployment executed |

PASS means the listed check ran successfully in the stated environment. FAIL means an executed failing check. NOT RUN means execution did not occur. NOT VERIFIED means configuration or incomplete evidence does not establish a capability. Old root TEST_RESULTS.md and PUBLICATION_STATUS.json are dated history, not current status.

## Preserved failed trial

Initial expanded CI https://github.com/yusufthecoder474/EventPulse-SRE/actions/runs/38998291730 at c3380be8fb810f85bd66095cc01386324bc936a2 passed 47 backend tests, frontend build/tests, stack startup, monitoring validation and persistence. Its same-namespace SIGKILL trial did not terminate PID 1; RestartCount stayed zero. This was a FAIL, not recovery evidence. See ci-initial-failure-summary.json and artifact 12088460706. The corrected, opt-in SIGUSR1 handler performs an abrupt os._exit(86); no HTTP crash endpoint was added.

## Measurement limits

One trial per scenario in the selected PR run, on a GitHub-hosted Ubuntu runner with Docker/PostgreSQL. Polling uses host-observed UTC timestamps and is not an exact internal Prometheus event trace. The automatic crash trial recovered before the 30s alert hold, so alert firing/resolution are null. Manual DB/API restoration is separate from automatic restart. Request p50/p95 include fast failed requests; they do not represent healthy-only latency or production capacity. No AWS, production uptime, financial savings or universal zero-downtime result is inferred.

Full request samples, observer events, JUnit and new screenshots: https://github.com/yusufthecoder474/EventPulse-SRE/actions/runs/38998784660/artifacts/12088202136 . Recorded summaries are committed under evidence/v2 for durable review.
