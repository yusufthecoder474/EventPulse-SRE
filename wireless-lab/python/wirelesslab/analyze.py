import json
import os
from pathlib import Path
import subprocess
import time
from .schema import WirelessEvent

LAB_ROOT = Path(__file__).resolve().parents[2]
MAX_EVENTS = 50000


class AnalyzerUnavailable(RuntimeError):
    pass


def binary_path():
    default = (
        LAB_ROOT
        / "cpp/build"
        / ("wireless_analyzer.exe" if os.name == "nt" else "wireless_analyzer")
    )
    return Path(os.getenv("WIRELESS_ANALYZER", str(default))).resolve()


def analyze_events(values, window_ms=5000):
    if not isinstance(values, list) or len(values) > MAX_EVENTS:
        raise ValueError("A bounded event list is required (maximum 50000)")
    if not 500 <= window_ms <= 60000:
        raise ValueError("window_ms must be 500..60000")
    events = [
        v if isinstance(v, WirelessEvent) else WirelessEvent.model_validate(v)
        for v in values
    ]
    records = [
        "\t".join(
            map(
                str,
                [
                    e.event_id,
                    e.timestamp_us,
                    e.client,
                    e.ap,
                    e.kind,
                    e.code,
                    e.sequence,
                    e.origin,
                    e.direction,
                    e.reported_state,
                ],
            )
        )
        for e in events
    ]
    executable = binary_path()
    if not executable.is_file():
        raise AnalyzerUnavailable("Build the C++17 analyzer with CMake first")
    start = time.perf_counter()
    try:
        process = subprocess.run(
            [str(executable), "--window-ms", str(window_ms)],
            input="\n".join(records) + ("\n" if records else ""),
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
            shell=False,
            cwd=str(LAB_ROOT),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AnalyzerUnavailable(
            "Analyzer unavailable or bounded execution timed out"
        ) from exc
    if process.returncode != 0 or len(process.stdout) > 2_000_000:
        raise ValueError("Analyzer rejected input or produced an oversized result")
    result = json.loads(process.stdout)
    if result.get("schema_version") != 1 or result.get("input_events") != len(events):
        raise ValueError("Invalid analyzer data contract")
    result["analysis_duration_ms"] = (time.perf_counter() - start) * 1000
    return result
