# Verification results — 16 October 2026

| Check | Observed result | Evidence |
|---|---|---|
| Python lint | Passed | evidence/lint.txt |
| Backend tests | 34 passed, 1 skipped | evidence/backend-tests.txt; backend-junit.xml |
| PostgreSQL integration | Skipped locally; PG_TEST_URL unavailable | backend/tests/test_postgres.py |
| Frontend unit tests | 3 passed | evidence/frontend-tests.txt |
| TypeScript and Vite build | Passed | evidence/frontend-build.txt |
| Real Chromium browser flows | 2 passed, desktop and mobile | evidence/browser-tests.txt; browser-junit.xml |
| HTTP experiments | 12 completed, 6 development + 6 held-out | evidence/experiments.json |
| Fault-window business requests | 3,060 observed (recovery requests excluded) | evidence/raw-experiments.json |
| Impact scenarios detected | 8 / 8 | scenario-level ground truth schedule + incident snapshots |
| False-positive scenarios | 0 / 4 baseline/noise cases | experiments.json |
| Scenario precision / recall | 100% / 100%; each Wilson 95% interval 67.56%–100% | experiments.json |
| Median first detection | 1.753s | 8 detected synthetic scenarios, 3s observation window |
| Median recorded incident recovery | 3.018s | incident end minus fault-clear time |
| Fresh recovery-probe success | 100% in each scenario | experiments.json |
| Docker build / Compose runtime | Not run: Docker unavailable | configuration included; CI configured |
| Prometheus/Grafana runtime / promtool | Not run locally | provisioning and validation commands included |
| Remote GitHub Actions | Not run; repository not published | configured workflow is not a passing CI run |
| GitHub publication | Blocked | connected tools lack repository creation; no CLI or terminal credential helper |

The authenticated GitHub login was verified as `yusufthecoder474`. The intended repository returned 404. No unrelated repository was modified. No remote commit or successful push is claimed. `PUBLISH_GITHUB.ps1` checks the account and absent target, reruns available checks, creates the public repository, pushes and verifies its remote branch once run in an authenticated GitHub CLI environment. It stops if the repository already exists.

## Scope and reproducibility

Python 3.12, FastAPI 0.135.1, SQLAlchemy 2.0.48 and pytest 9.0.2 were used for final backend verification. Backend local tests and real HTTP experiments used file-backed SQLite, **not PostgreSQL**. The dedicated PostgreSQL test is implemented and wired to a PostgreSQL 16 GitHub Actions service, but that remote job has not run.

The normal Playwright browser download failed in this restricted environment. Browser flows were successfully run using a Chromium 153 binary obtained from the npm serverless Chromium package, with an explicit executable-path override and software rendering; the standard Playwright setup remains the default for user/CI runs. Two workers isolate browser processes because the restricted single-process browser could not reopen a second context sequentially. Initial failed environment attempts are superseded by the final captured two-pass browser report. Screenshots are actual captures, not generated mockups.

The system package installer and standalone PostgreSQL setup were attempted; process ownership restrictions prevented PostgreSQL startup. This is recorded as unverified rather than treating SQLite evidence as equivalent. The Starlette TestClient emits one deprecation warning about httpx; tests still pass. Longer-window Prometheus alerts and Alertmanager delivery were not exercised by the short-window HTTP evaluation.

The experiment protocol is synthetic, single-host and small. Wilson intervals assume binomial-style independent observations; repeated scenarios on one machine weaken that assumption. No production effectiveness, operational savings or capacity claims follow from these results. See EVALUATION.md for denominators, held-out split and offline comparison limitations.
