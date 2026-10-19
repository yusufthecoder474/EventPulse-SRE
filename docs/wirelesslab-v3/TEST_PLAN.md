# Automated feature-validation plan

Source: `wireless-lab/scenarios/test-plan-v3.json`. Each definition carries ID, feature, preconditions, fixture, expected behavior, origin and reproduction command. Execution adds observed behavior, verdict, classification, event references, duration and detailed analysis. IDs are registry entries, never user paths or commands.

| Cases | Unique scenarios | Evidence |
|---|---:|---|
| A–J | 10 | Original five generated PCAP + five JSON event scenarios |
| P01–P10 | 10 | Synthetic WPA2 header-metadata event fixtures |
| C01–C04 | 4 | Synthetic cross-layer state fixtures |
| Total | 24 | Deterministic and hardware-independent |

PASS means expected behavior matched, including expected association rejection, missing evidence and stale state. A correctly reproduced negative connection outcome is a passing **validation**. Suite counters explicitly separate unique definitions, executed runs, passed runs and validation failures. Imported captures use `analysis_only`, not pass/fail against an invented expectation. Repeated execution increases run counts, not unique scenario count.

```bash
python wireless-lab/scripts/validate_v3.py --test P03
python wireless-lab/scripts/validate_v3.py --output /tmp/v3-plan-new.json
python wireless-lab/scripts/validate_v3.py --output /tmp/v3-replay-new.json --compare /tmp/v3-plan-new.json
python wireless-lab/scripts/evaluate_handshakes.py --output /tmp/v3-heldout-new.json
```

Each output writes JSON, with CSV and human-readable Markdown for plans. Existing evidence output paths are refused. Regression comparison compares stable per-ID verdict/classification sets, excluding timing; added/removed/mismatching IDs fail the command. Held-out evaluation publishes a seeded input dataset and SHA256 so the evaluation is reproducible.

Guest GET `/plans` lists definitions; POST `/validations` runs one ID or all; owner-scoped `/runs/{id}/validation-export` returns JSON/CSV. The full plan consumes one expensive-operation quota, uses only approved fixtures and shares four execution slots with capture imports and legacy scenario runs. It has a 30-second deadline checked between cases, plus bounded per-stage subprocess timeouts; it is not a hard whole-process kill at exactly 30 seconds. No live network dependency exists.

CI adds sanitizers, V3 plan/replay comparison, held-out classification and benchmarks to the original build/lint/Python/frontend/Compose/monitoring/persistence/recovery/browser workflow. Regression commands return nonzero on any mismatch. Dependency and test reports are uploaded as artifacts. Exact executed outcomes and skips are in TEST_RESULTS.md.
