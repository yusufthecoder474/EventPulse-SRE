"""Real process/HTTP checks for Bash operations plus observer unit boundaries."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from app.telemetry import Telemetry

ROOT = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def native_api(tmp_path_factory):
    temporary = tmp_path_factory.mktemp("native-v2")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ)
    env.update(DATABASE_URL="sqlite:///" + str(temporary / "native.db"), ENABLE_FAULTS="false", API_URL=f"http://127.0.0.1:{port}")
    with (temporary / "api.log").open("w") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.server:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT / "backend",
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for _ in range(100):
                try:
                    if opener.open(env["API_URL"] + "/health/ready", timeout=0.5).status == 200:
                        break
                except OSError:
                    time.sleep(0.05)
            else:
                raise RuntimeError("Native API did not become ready")
            yield env
        finally:
            process.terminate()
            process.wait(timeout=10)


@pytest.mark.skipif(os.name == "nt", reason="Bash automation runs under Linux/WSL or CI")
def test_real_bash_health_and_registration_smoke(native_api):
    for script in ("health-check.sh", "smoke-test.sh"):
        result = subprocess.run(["bash", str(ROOT / "scripts" / script)], env=native_api, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    env = {**native_api, "SMOKE_EXPECT_EXISTING": "true"}
    result = subprocess.run(["bash", str(ROOT / "scripts/smoke-test.sh")], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "idempotency" in result.stdout


@pytest.mark.skipif(os.name == "nt", reason="Bash syntax check requires Linux/WSL")
@pytest.mark.parametrize("script", ["lib.sh", "health-check.sh", "smoke-test.sh", "verify-stack.sh", "collect-diagnostics.sh", "deploy-local.sh"])
def test_bash_syntax(script):
    subprocess.run(["bash", "-n", str(ROOT / "scripts" / script)], check=True)


@pytest.mark.skipif(os.name == "nt", reason="Bash automation runs under Linux/WSL")
def test_health_rejects_nonloopback_target():
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/health-check.sh")], env={**os.environ, "API_URL": "http://example.test:8000"}, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "loopback" in result.stderr


def test_error_series_exist_before_first_failure():
    telemetry = Telemetry()
    for status in ("500", "503", "504"):
        assert telemetry.registry.get_sample_value("eventpulse_http_requests_total", {"method": "GET", "route": "/events", "status": status}) == 0
    assert telemetry.summary()["availability"] is None


def test_observer_counts_transport_failure_and_tail_latency():
    observer = load_script("reliability")
    measured = observer.summarize(
        [{"duration_seconds": 0.01, "status": 200}, {"duration_seconds": 1.2, "status": None}, {"duration_seconds": 0.5, "status": 503}]
    )
    assert measured["total_requests"] == 3
    assert measured["failed_requests"] == 2
    assert measured["p95_seconds"] == 1.2
    assert observer.summarize([])["error_percentage"] is None
    assert observer.utc().endswith("+00:00")


def test_observer_refuses_unapproved_fault():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/reliability.py"), "--scenario", "api-crash", "--project", "production"], capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "Explicit" in result.stderr


def test_monitoring_panels_use_actual_metric_expressions():
    dashboard = json.loads((ROOT / "monitoring/grafana/dashboards/eventpulse.json").read_text())
    assert len(dashboard["panels"]) == 15
    assert any("budget remaining" in p["title"] for p in dashboard["panels"])
    assert any("histogram_quantile(0.5" in p["targets"][0]["expr"] for p in dashboard["panels"])


def test_crash_hook_disabled_by_default(monkeypatch):
    from app.crash_lab import install_crash_handler
    monkeypatch.delenv("ENABLE_PROCESS_CRASH_TEST", raising=False)
    assert install_crash_handler() is False


def test_crash_hook_requires_local_environment(monkeypatch):
    from app.crash_lab import install_crash_handler
    monkeypatch.setenv("ENABLE_PROCESS_CRASH_TEST", "true")
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        install_crash_handler()


@pytest.mark.skipif(os.name == "nt", reason="POSIX signal hook")
def test_crash_hook_exits_abruptly_when_explicitly_enabled(monkeypatch):
    import signal
    import app.crash_lab as crash
    monkeypatch.setenv("ENABLE_PROCESS_CRASH_TEST", "true")
    monkeypatch.setenv("APP_ENV", "local")
    saved = {}
    monkeypatch.setattr(signal, "signal", lambda number, handler: saved.update(number=number, handler=handler))
    monkeypatch.setattr(os, "_exit", lambda code: saved.update(exit_code=code))
    assert crash.install_crash_handler()
    saved["handler"](signal.SIGUSR1, None)
    assert saved["exit_code"] == 86
