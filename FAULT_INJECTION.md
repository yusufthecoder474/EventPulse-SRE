# Fault injection lab

Disabled by default. Only native local use is supported; Compose disables mutations. No automated fault can stop your actual database, change host networking or contact third parties.

From root, generate `.env` using `python scripts/bootstrap.py`. In a PowerShell terminal, read its values, opt in and start a fresh evidence database:

```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') } }
$env:ENABLE_FAULTS = 'true'
$env:APP_ENV = 'local'
$env:OBSERVATION_WINDOW_SECONDS = '3'
$env:DATABASE_URL = 'sqlite:///./lab.db'
$env:EVIDENCE_PATH = '../evidence/experiments.json'
cd backend
python -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

Start Vite in another terminal and open http://127.0.0.1:5173. Paste your local FAULT_TOKEN into the lab password field. Select a fault, send probes, inspect Incident Center, clear the fault and send recovery probes. TTL is 30s in the UI, bounded to 1..120s in the API. `every` can affect every Nth request, delay range is 0..3000ms. A new injection replaces the previous fault; multiple simultaneous fault types are not supported.

| Fault | User impact | Actual dependency state |
|---|---|---|
| latency | actual awaited delay on business requests | database remains running |
| http500 | HTTP 500 | database remains running |
| dependency | awaited delay then HTTP 504 | synthetic downstream timeout |
| database | HTTP 503 and readiness false | simulated failure, database remains running |
| warning | JSON warning logs, normal response | no expected impact |

The lab endpoint rejects disabled mode, incorrect/short token, non-loopback socket peer and untrusted browser Origin. It ignores forwarded IP headers. Never change Vite/API bind to 0.0.0.0 for this native lab. Notes use the same local authorization and can be saved after entering the token on the lab page.

## Automated evaluation

In the evaluator terminal, set FAULT_TOKEN to the same local generated value, then from root run `python scripts/evaluate.py`. Use a fresh lab database for clean incident evidence. The script sends actual HTTP traffic, labels truth from the predefined scenario schedule, clears faults and verifies fresh successful responses. It expects a short <=5s window; defaults to 4s of affected traffic and window+1.5s recovery traffic. Results overwrite historical experiment JSON files. The integrated runner `python scripts/verify_local.py` performs the same procedure with ephemeral in-memory credentials and SQLite, followed by browser tests.

Actual database interruption rehearsal with Compose (fault lab off): `docker compose stop db`, send GET /events and inspect readiness/Grafana, then `docker compose start db` and re-probe. This is a manual, separate real dependency experiment; do not confuse it with the simulated evidence. Do not claim it was run unless it was.
