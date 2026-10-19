import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from wirelesslab.scenarios import definitions, run_scenario  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=[s["id"] for s in definitions()])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    chosen = [args.scenario] if args.scenario else [s["id"] for s in definitions()]
    results = [run_scenario(s) for s in chosen]
    output = args.output or ROOT / "evidence" / (
        "scenarios-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
    )
    output.parent.mkdir(exist_ok=True, parents=True)
    if output.exists():
        raise SystemExit("Refusing to overwrite historical scenario evidence")
    report = {
        "origin": "Synthetic laboratory fixtures, not real Cisco equipment",
        "scenarios_executed": len(results),
        "passed": sum(r["verdict"] == "pass" for r in results),
        "runs": results,
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "runs"}))
    raise SystemExit(0 if report["passed"] == len(results) else 1)


if __name__ == "__main__":
    main()
