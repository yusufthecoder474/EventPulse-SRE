# v2 verification report

Base source: main 0a6efd1c09ff30cdb0ff838da7d79ba858582e10. No project ZIP was attached; source was obtained by cloning the specified existing repository. Original POSTMORTEM.md, screenshots and evidence remain unchanged. Audit: AUDIT_V2.md.

| Capability | Status before remote v2 CI | Evidence / boundary |
|---|---|---|
| Baseline GitHub Actions | PASS | run 38942106723 and individual steps verified via GitHub API |
| Local Python lint | PASS | evidence/v2/lint.txt |
| Local backend tests | PASS: 46 passed; 1 PostgreSQL test skipped | evidence/v2/backend-tests.txt, backend-junit.xml |
| Bash syntax / ShellCheck | PASS | six scripts plus host setup inspected with bash -n/ShellCheck; ShellCheck empty output means no findings |
| Real Bash health and API smoke | PASS | native API subprocess test in test_v2_automation.py |
| Frontend unit tests | PASS: 3 passed | evidence/v2/frontend-tests.txt |
| Frontend build | See build output | evidence/v2/frontend-build.txt |
| New Docker / PostgreSQL stack integration | NOT RUN locally | Docker unavailable; new CI workflow will run it |
| New Prometheus rule fixtures | NOT RUN locally | promtool absent; new CI workflow will run them |
| Automatic Docker crash recovery | NOT VERIFIED until observer artifact reviewed | restart policy and safe isolated test implemented |
| New exact manual outage timestamps | NOT VERIFIED until observer artifact reviewed | new observer implemented; historical manual evidence preserved |
| Blue-green experiment | NOT RUN / deferred | scoped future plan in PERFORMANCE_REPORT.md |
| AWS deployment | NOT VERIFIED | template and instructions only; no approval or cloud operations |
| Backup/restore round trip | NOT RUN | no unverified backup script added |

PASS indicates an executed successful check. FAIL indicates an executed failing check. NOT RUN means a check was not executed in the stated environment. NOT VERIFIED means the capability lacks sufficient execution evidence even if configuration exists. Dated root TEST_RESULTS.md and PUBLICATION_STATUS.json are historical and not the current publication status. The current feature branch/PR/run must be recorded after actual publication.
