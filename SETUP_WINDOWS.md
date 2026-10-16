# Windows setup

Install Python 3.12+, Node 22 LTS, Git and Docker Desktop (WSL2 backend). Run commands from an extracted project folder. If PowerShell activation is restricted, use `.venv\Scripts\python.exe` directly instead of changing machine execution policy.

## Full PostgreSQL stack

```powershell
python scripts/bootstrap.py
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs api
```

Open http://localhost:8080. Credentials are generated in `.env`; never upload that file. Stop with `docker compose down`. Named volumes preserve database, Prometheus and Grafana data. Do not use `down -v` unless you intend to discard local data.

## Native PostgreSQL API with dashboard

```powershell
docker compose up -d db
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
# Read local generated values into this terminal only.
Get-Content .env | ForEach-Object { if ($_ -match '^([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') } }
$env:DATABASE_URL = "postgresql+psycopg://eventpulse:$($env:POSTGRES_PASSWORD)@127.0.0.1:5432/eventpulse"
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

Second terminal: `cd frontend`, `npm ci`, `npm run dev`. Open http://127.0.0.1:5173. If Compose API already occupies 8000, run `docker compose stop api web` first. PostgreSQL port 5432 must be free. Native mode without DATABASE_URL uses SQLite. Start PostgreSQL before the API; schema creation is deliberately fail-fast.

## Troubleshooting

Connection refused: inspect `docker compose ps`, `docker compose logs db` and the DATABASE_URL value locally. Do not post credentials in screenshots. API returns no SLI data: click Send 10 probes; health/monitoring requests do not count toward business SLIs. Port in use: stop the earlier service. Frontend offline: API must run on 8000 and Vite on 5173. Readiness red: check database probe and active simulated fault. Fault control 403: native loopback lab, correct token, explicit enablement and valid Origin are all required.

## PostgreSQL test database

Create a separate database `eventpulse_test` locally. Set `PG_TEST_URL` to its connection URL, then run `cd backend; python -m pytest tests/test_postgres.py -q`. This check truncates its own tables. Never target normal application data.
