# CI and deployment automation

Baseline main commit `0a6efd1c09ff30cdb0ff838da7d79ba858582e10` has a verified successful workflow: https://github.com/yusufthecoder474/EventPulse-SRE/actions/runs/38942106723 . This evidence corrects older, dated documentation that said the initial workflow had not run. It does not establish success of a new workflow revision.

The v2 workflow runs on main/feat branches, PRs to main and manual dispatch. It installs dependencies, checks Python/Bash and staged/tracked credential patterns, runs PostgreSQL integration tests, frontend tests/build, validates Compose, builds and launches all six containers, validates Prometheus/Alertmanager configurations and promtool test cases, runs synthetic API smoke and persistence assertions, measures actual API process-crash recovery and separate manual database/API outages, then runs real desktop/mobile browser flows. New artifacts go under evidence/v2. Isolated CI project: eventpulse-v2-ci. Cleanup stops containers without deleting volumes on users' machines.

The PostgreSQL test service uses port 5433 while the full stack uses 5432. Credentials are fixed synthetic CI-only database values or locally generated .env values. Local .env is never committed or included in artifacts. The secret scanner is heuristic and not a guarantee; publication also requires manual diff review. Static Bash checks and native-API script tests are distinct from Docker integration.

CI uploads `eventpulse-v2-verification`, including machine-readable observer events, request totals/latencies and JUnit. Record the **actual** workflow URL, tested SHA, conclusion and artifact ID in VERIFICATION_REPORT.md. A feature-branch push and a PR may trigger separate runs; inspect the run for the intended SHA. Failed runs must be reviewed and fixed, not renamed as passes.

`scripts/deploy-local.sh` is an opt-in in-place deployment on an existing host, gated on a clean checkout and reviewed full commit SHA. It does not create AWS resources, SSH to a target, provide zero downtime or turn build CI into a cloud CD success. No AWS credentials are in GitHub Actions. A cloud CD workflow should be added only after a target, short-lived identity model and approval are established.

## Safe Git update from Windows

```powershell
git status
git remote -v
git fetch origin
# Stop and preserve your changes if git status is not clean.
git switch -c feat/sre-v2-automation origin/main
# Apply the reviewed v2 files; preserve local .env and existing evidence.
git add .github backend compose.yml frontend monitoring scripts deploy docs README.md PUBLISH_GITHUB.ps1 RESUME_EVIDENCE_V2.md CHANGELOG_V2.md
python scripts/check_publish.py
git diff --cached --check
git diff --cached --stat
git commit -m "feat: strengthen SRE automation, reliability metrics and deployment validation"
git push -u origin feat/sre-v2-automation
# Open a PR to main; do not force-push.
```

If the delivered feature branch already exists remotely, use `git switch --track origin/feat/sre-v2-automation` instead of creating a branch with the same name. Use the provided PR rather than copying files over a newer main branch. The replacement PowerShell publishing helper stops on uncommitted changes or unexpected remote and only pushes the current feature branch; it never creates a repository or forces history.

## Verified v2 run

https://github.com/yusufthecoder474/EventPulse-SRE/actions/runs/38998784660 completed SUCCESS for `1b98638c7f4cd289434d0cf49b5e3f8e5e1f522a`, including all integration, observer and browser steps. Artifact 12088202136 contains the raw measurements and screenshots. The final report records the tested SHA explicitly; later documentation-only commits are not silently treated as having that run's SHA.
