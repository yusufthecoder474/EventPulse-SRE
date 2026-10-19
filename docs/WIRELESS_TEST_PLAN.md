# Wireless test plan

> Initial WirelessLab release guide retained as historical context. For current V3 import/handshake/test-plan capabilities and boundaries, see [V3 architecture](wirelesslab-v3/ARCHITECTURE.md) and [V3 results](wirelesslab-v3/TEST_RESULTS.md). The legacy operator-only `/uploads` remains restricted; V3 adds a separate consent-bound `/imports` endpoint.

## Reproduce

```bash
cmake -S wireless-lab/cpp -B wireless-lab/cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build wireless-lab/cpp/build -j2
ctest --test-dir wireless-lab/cpp/build --output-on-failure
python -m pip install -r backend/requirements-dev.txt
(cd backend && python -m pytest tests ../wireless-lab/tests -q)
python wireless-lab/scripts/run_scenarios.py
(cd frontend && npm ci && npm test && npm run build)
# Start API (port 8000), then:
(cd frontend && npx playwright install chromium && npm run test:e2e)
python wireless-lab/scripts/evaluate.py --output wireless-lab/evidence/performance-new.json
```

TShark must be installed for the full suite. PostgreSQL integration uses `PG_TEST_URL`; without it, its one test is explicitly skipped. Browser tests use the real running API through Vite, not mocked analysis responses. On a normal workstation the Compose startup from README provides the API. Restricted-container local evidence used an extracted Chromium executable and four workers to avoid single-process browser-context reuse; CI uses the official Playwright Chromium runtime.

## Coverage

CTest covers success, rejection, authentication failure, disconnection, DHCP, DNS, latency, correlation window, duplicates, disorder, empty and malformed input, numeric errors, deterministic output, management disagreement, Ethernet-only EAPOL, invalid synthetic transition, key-message observations, SAE, multiple clients and reconnection. Python tests validate the ten scenarios, real TShark packet decoding and privacy, missing fields, radio/Ethernet distinction, time preservation, schema validation, safe subprocess options/timeouts and path limits. API tests validate cookie/CSRF/expiry, per-owner runs/APs/exports, guest upload denial, quotas, typed payloads, AP bounds, metrics and original endpoint availability. Existing regression tests remain unchanged.

Browser flows cover original console navigation/probes/mobile, one-click guest entry, real scenario B, expected-versus-actual failure diagnosis, packet A EAPOL filtering, export link, denied guest upload, all seven mobile views and horizontal overflow. Role/name selectors and labeled form inputs provide basic accessibility checks; no formal WCAG certification, screen-reader audit or automated axe scan is claimed.

## Scenario matrix

| ID | Objective / actual expected classification | Evidence |
|---|---|---|
| A | Successful association | Generated PCAP |
| B | AP rejection | Generated PCAP |
| C | Authentication rejection | Generated PCAP |
| D | Explicit disconnection | Generated PCAP |
| E | DHCP failure after join | Synthetic JSON |
| F | DNS failure after IP configuration | Synthetic JSON |
| G | Request/response association delay | Generated PCAP |
| H | Duplicate and out-of-order handling | Synthetic JSON |
| I | Missing context remains incomplete | Synthetic JSON |
| J | Stale/inconsistent controller observation | Synthetic JSON |

`scenarios/catalog.json` specifies each objective, preconditions, exact fixture, expected classifications, provenance and reproduction command. Timestamped `evidence/scenarios-*.json` adds actual behavior, assertions, pass/fail and normalized event evidence for every scenario. PASS includes correctly reproduced negative outcomes; it never means every association succeeded. Ten deliberately designed fixtures cannot estimate real-world false-positive rates.

CI retains the original lint, secrets, frontend unit/build, Docker Compose, PostgreSQL, monitoring validation, live persistence, crash/outage recovery and browser checks. It adds CMake/CTest, Python wireless tests, real scenario orchestration and dependency scans. Production dependencies gate CI; existing development dependency advisories are reported in a visible non-blocking step. Workflow configuration alone is not evidence of success; consult the linked real run in test results.
