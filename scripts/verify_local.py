"""Run API, Vite, real HTTP evaluation and browser verification in one local process tree."""

import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
env = dict(os.environ)
env.update(
    FAULT_TOKEN=secrets.token_hex(24),
    ENABLE_FAULTS="true",
    APP_ENV="local",
    OBSERVATION_WINDOW_SECONDS="3",
    EVIDENCE_PATH=str(ROOT / "evidence/experiments.json"),
    DATABASE_URL="sqlite:///" + str(ROOT / "backend/verification.db"),
)
# No generated credentials are written into evidence.
api_log = open("/tmp/eventpulse-verification-api.log", "w")
web_log = open("/tmp/eventpulse-verification-web.log", "w")
api = subprocess.Popen(
    [
        sys.executable,
        "-m",
        "uvicorn",
        "app.server:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ],
    cwd=ROOT / "backend",
    env=env,
    stdout=api_log,
    stderr=subprocess.STDOUT,
)
web = subprocess.Popen(
    ["npm", "run", "dev"],
    cwd=ROOT / "frontend",
    env=env,
    stdout=web_log,
    stderr=subprocess.STDOUT,
)
try:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for url in ["http://127.0.0.1:8000/health/live", "http://127.0.0.1:5173"]:
        for _ in range(100):
            try:
                opener.open(url, timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError(f"Service did not start: {url}")
    with open(
        ROOT / "evidence/evaluation-log.txt",
        "a" if "--browser-only" in sys.argv else "w",
    ) as output:
        result = (
            subprocess.CompletedProcess([], 0)
            if "--browser-only" in sys.argv
            else subprocess.run(
                [sys.executable, str(ROOT / "scripts/evaluate.py")],
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
        )
    print("HTTP evaluation exit code:", result.returncode, flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    with open(ROOT / "evidence/browser-tests.txt", "w") as output:
        result = subprocess.run(
            ["npm", "run", "test:e2e"],
            cwd=ROOT / "frontend",
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
    print("Browser test exit code:", result.returncode, flush=True)
    raise SystemExit(result.returncode)
finally:
    api.terminate()
    web.terminate()
    api.wait(timeout=10)
    web.wait(timeout=10)
