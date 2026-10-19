"""Execute registered plans; compare stable verdicts/classes with previous JSON evidence."""

import argparse
import csv
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from wirelesslab.validation import execute_plan  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--test")
    p.add_argument("--output", type=Path)
    p.add_argument("--compare", type=Path)
    a = p.parse_args()
    report = execute_plan(a.test)
    if a.compare:
        previous = json.loads(a.compare.read_text())
        before = {
            r["test_id"]: (r["verdict"], r["observed_behavior"])
            for r in previous["results"]
        }
        after = {
            r["test_id"]: (r["verdict"], r["observed_behavior"])
            for r in report["results"]
        }
        report["regression_comparison"] = {
            "matches": before == after,
            "differences": [
                k for k in before.keys() | after.keys() if before.get(k) != after.get(k)
            ],
        }
    if a.output:
        if a.output.exists():
            raise SystemExit("Refusing to overwrite historical evidence")
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(report, indent=2) + "\n")
        buffer = io.StringIO()
        w = csv.DictWriter(
            buffer,
            fieldnames=[
                "test_id",
                "feature",
                "verdict",
                "expected_behavior",
                "observed_behavior",
                "execution_duration_ms",
                "reproduction",
            ],
        )
        w.writeheader()
        for r in report["results"]:
            w.writerow({k: r[k] for k in w.fieldnames})
        a.output.with_suffix(".csv").write_text(buffer.getvalue())
        a.output.with_suffix(".md").write_text(
            "# Synthetic wireless test report\n\n"
            + "\n".join(
                f"- {r['test_id']}: {r['verdict']} — expected {r['expected_behavior']}; observed {r['observed_behavior']}"
                for r in report["results"]
            )
            + "\n"
        )
    print(json.dumps({k: v for k, v in report.items() if k != "results"}))
    raise SystemExit(
        1
        if report["validation_failures"]
        or not report.get("regression_comparison", {}).get("matches", True)
        else 0
    )


if __name__ == "__main__":
    main()
