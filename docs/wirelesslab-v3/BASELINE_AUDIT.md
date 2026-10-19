# Baseline audit — before implementation

Latest main: `771352aedd632a839f9290b2406e4904289c801e`; tree `62135ab54813f5c2dd50e18374f21a7dd41e2d72`. Uploaded EventPulse-SRE-main.zip matches every archived file byte-for-byte. Working tree was clean; branch `feature/wirelesslab-v3-cisco-validation` starts from that main. Earlier isolated feature work is not overwritten. No AGENTS.md found. No secrets or environment files changed.

Architecture inspected: FastAPI main/database/telemetry/crash_lab, SQLAlchemy on existing SQLite/PostgreSQL, six original React pages plus seven WirelessLab sections, compose.yml, backend/frontend Dockerfiles, Prometheus rules, Alertmanager, original 15-panel Grafana dashboard plus separate wireless dashboard, Bash bootstrap/smoke/monitoring/recovery scripts, CI, all existing tests, README and wireless architecture/security/test-results guides. CI retains Compose persistence and controlled outage recovery checks. No extra database is needed.

Wireless entry points: cpp/analyzer.cpp (ten-column TSV, stable sorting, semantic deduplication, per client/AP state), python/wirelesslab/{packets,schema,analyze,scenarios}.py (real TShark file extraction, Pydantic, bounded C++ subprocess, A–J registry), scripts/generate_fixtures.py (stdlib synthetic packet writer), backend/app/wireless_api.py (guest ownership, runs/APs/exports), frontend/src/WirelessLab.tsx. Guest cookies are random, HttpOnly, SameSite Strict, one hour; hash stored in existing DB; per-owner quotas, histories and AP bounds. Original `/uploads` is local-operator-only and must remain restricted. Schema v1 currently reports EAPOL message sets, not sequence/replay-counter validation. Import rejects captures without supported normalized events and lacks explicit container metadata.

Fresh pre-change checks, Linux/GCC 13.3/Python 3.12/TShark 4.2.2/Node 24/Chromium:

| Check | Passed | Failed | Skipped |
|---|---:|---:|---:|
| CTest | 21 | 0 | 0 |
| Python/API | 83 | 0 | 1 (native PostgreSQL unavailable locally) |
| Frontend unit | 3 | 0 | 0 |
| Real browser flows | 4 | 0 | 0 |
| TypeScript/Vite production build | pass | 0 | 0 |

Raw baseline reports are in `wireless-lab/evidence/v3/baseline/`. TShark and Chromium were extracted into temporary paths without installing capture privileges. Local Docker is unavailable; full Compose verification will run in real GitHub Actions. Historical run [39233891910](https://github.com/yusufthecoder474/EventPulse-SRE/actions/runs/39233891910) was independently queried and is successful for its implementation commit, with 84 Python/API tests including PostgreSQL. This is historical evidence, not verification of new V3 code. Main's source matches the uploaded code but the workflow query wrapper only exposes PR runs, so no separate latest-main run is inferred.

Planned compatible additions: optional TSV metadata columns, dedicated C++ handshake state analysis, strict container preflight plus maintained TShark decoding, a new guest-authorized import endpoint with consent and shared execution bounds, independent machine-readable V3 plans, cross-layer evidence, and small panels inside existing views. Real capture/hardware, WPA3, MSVC and production deployment remain unverified.
