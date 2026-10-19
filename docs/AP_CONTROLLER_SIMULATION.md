# Simulated management plane and API

Every guest receives three synthetic inventory APs with locally administered BSSIDs and a fixed demo SSID. Registering an AP adds a database row only. The `simulated online` status is a model label, not a reachability or hardware health probe. Inventory registration does not dynamically generate packets or alter the fixed scenario fixtures. Client summaries derive from the latest retained scenario per client/AP pair.

Scenario J models an explicit AP acceptance, later disconnection and a stale controller `connected` update. C++ compares the controller view to the last explicit AP state, reports disagreement, and measures lag using the common synthetic clock. This can demonstrate stale management data without establishing a vendor bug or actual network outage.

## HTTP contract

Routes below are prefixed `/wireless-lab` (browser proxy `/api/wireless-lab`). OpenAPI `/docs` contains typed request schemas. Mutations require `X-Wireless-Demo: 1`; browser origin must be allowlisted. For a same-host deployed demo set `WIRELESS_ALLOWED_ORIGINS` to its exact public origin. Cookie-based guest ownership is required except capabilities and guest entry.

| Method | Route | Behavior |
|---|---|---|
| GET | `/capabilities` | Dependency availability, guest limits, explicit non-hardware scope |
| POST | `/guest` | Server-issued HttpOnly SameSite=Strict cookie, one hour |
| GET / DELETE | `/session` | Read expiry / remove own data and session |
| GET / POST | `/aps` | List / register bounded synthetic inventory |
| GET | `/clients` | Latest per-pair analysis from this guest's history |
| GET | `/scenarios`, `/fixtures` | Approved catalog and provenance |
| POST | `/runs` | `{ "scenario_id": "A" }` through actual parser/analyzer |
| GET | `/runs`, `/runs/{id}` | Own retained history / full investigation |
| GET | `/runs/{id}/events` | Normalized annotated events |
| GET | `/runs/{id}/export?format=json|csv` | Sanitized attachment |
| GET | `/fixtures/{A..J}/capture` | Generated-PCAP IDs only; JSON fixture IDs return 404 |
| POST | `/uploads` | Guest denied; opt-in local operator only (security document) |

Errors use structured `detail` messages and appropriate 401/403/404/409/413/422/429/503 codes; inaccessible run IDs return 404. No arbitrary command or path argument exists. Only a hash of the opaque cookie is stored. Twelve expensive operations/minute/session, twenty retained runs, eight inventory APs and 128 active guests bound demo use. Four scenario subprocess pipelines execute concurrently at most per API instance. The application runs one worker in the shipped Docker command; process-local admission/concurrency gates are not distributed quotas.
