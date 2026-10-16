# Evaluation protocol

The protocol and scenario labels are declared in scripts/evaluate.py before the test run. Six development cases cover baseline, latency, 500 errors, simulated database failure, dependency timeout, and warning noise. Six held-out cases use a second baseline, unseen 950ms delay, every-third-request errors, repeated database fault affecting alternate requests, an 800ms dependency timeout affecting alternate requests, and a second warning-noise case. Thresholds are not tuned on held-out results.

Ground truth is independent of detector output: the scenario schedule declares expected user impact before fault injection. This tests detection of controlled, known failures rather than discovering unknown real incidents. The truth is appropriate for the synthetic protocol only. Response samples independently confirm status and duration. All HTTP requests target localhost; no real attendee data is used.

Metrics are **scenario-level** precision TP/(TP+FP), recall TP/(TP+FN), false-positive scenario count, first matching local incident start minus scenario start, and last matching incident end minus fault-clear time. A scenario may trigger both latency and availability, but counts as one detected incident scenario. Timing includes observer sampling. Null recovery means no matching fully resolved incident. Recovery also requires fresh GET /events success; a cleared predicate alone is insufficient. Request success means <500, so latency-only incidents can have 100% HTTP success.

Raw evidence contains per-request start time, client latency, HTTP status, scenario start/clear times and saved incident snapshots. Quantiles use nearest rank on client-observed end-to-end durations, distinct from server middleware timings. CI data is not mixed with experiment data. The harness uses 4 concurrent workers. Counts are observed rather than predetermined.

A second, conservative **offline aggregate classifier** compares error ratio >20% or p95 >1s with the default >5% or >500ms. It uses the same measured scenario aggregates and does not replay rolling windows, hold periods, Prometheus or alert timing. Configuration-comparison JSON and UI explicitly state that limitation.

Wilson 95% intervals are provided for scenario precision/recall and request success where denominators exist. Small scenario samples have wide intervals. Runs share one machine and synthetic failure design, so independence assumptions are limited; no statistical significance, production accuracy, cost savings or operational ROI is claimed. More repetitions, independently generated scenarios and actual PostgreSQL outage trials are needed for stronger conclusions.

See evidence/experiments.json for exact results, evidence/raw-experiments.json for audit data, and TEST_RESULTS.md for verification scope. The short-window local detector and long-window Prometheus alerts are different configurations; the evaluation does not validate end-to-end Alertmanager delivery.
