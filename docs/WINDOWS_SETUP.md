# Windows setup

No radio adapter is required. Install Python 3.12, Node 22+, Git, CMake, Visual Studio Build Tools with Desktop development with C++, and official Wireshark/TShark. Add the Wireshark installation directory to PATH. TShark is used to read files; no live capture or Npcap capture permission is needed for this demo.

In PowerShell from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
cmake -S wireless-lab/cpp -B wireless-lab/cpp/build
cmake --build wireless-lab/cpp/build --config Release
$env:WIRELESS_ANALYZER = (Resolve-Path wireless-lab/cpp/build/Release/wireless_analyzer.exe).Path
ctest --test-dir wireless-lab/cpp/build -C Release --output-on-failure
tshark --version
python wireless-lab/scripts/run_scenarios.py
Set-Location backend
python -m pytest tests ../wireless-lab/tests -q
$env:DATABASE_URL = 'sqlite:///./eventpulse.db'
python -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

In a second PowerShell window, enter `frontend`, run `npm ci` then `npm run dev`. Open `http://127.0.0.1:5173/?lab=wireless` and choose Continue as Guest. Keep `WIRELESS_ANALYZER` set in the API process environment. A Ninja single-configuration build places the executable directly in `build` instead of `build/Release`.

For the complete original Prometheus/Grafana/PostgreSQL stack, Docker Desktop may run `python scripts/bootstrap.py` and `docker compose up --build -d --wait` as documented in README. Review generated local `.env` yourself; it is ignored and never committed. Docker Desktop does not imply mac80211_hwsim availability. MSVC and Windows execution instructions are provided but were not run in this Linux evidence session.
