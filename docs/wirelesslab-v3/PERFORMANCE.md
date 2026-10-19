# V3 performance evidence

Primary report: [`performance-quiet.json`](../../wireless-lab/evidence/v3/performance-quiet.json). Reproduction: `python wireless-lab/scripts/benchmark_v3.py --output /tmp/wireless-v3-benchmark-new.json`. The initial shared-workload run is also retained as `performance.json`; it is not silently overwritten. The primary run was repeated after browser/regression activity completed. This is still a shared development container, not an isolated production benchmark.

Environment: Linux 6.18.55 x86_64/glibc 2.39, AMD EPYC 9V74 host CPU, nine logical CPUs exposed, Python 3.12.14, GCC 13.3, TShark 4.2.2 and Release C++ build. All packets are generated Ethernet EAPOL with zero cryptographic placeholders. No real network timing, RF throughput, Cisco scale or cross-language comparison is inferred.

| Capture | Bytes | Packets | Direct pipeline p50 / p95 ms | HTTP import p50 / p95 ms |
|---|---:|---:|---:|---:|
| small | 540 | 4 | 141.827 / 162.118 | 243.773 / 985.867 |
| medium | 12924 | 100 | 170.043 / 204.826 | 238.385 / 322.937 |
| large_bounded | 258024 | 2000 | 274.056 / 325.829 | 546.539 / 602.357 |

Each capture size has seven direct pipeline and seven real loopback HTTP POST repetitions, one request in flight. Direct calls warm field discovery first. The HTTP server is a separate real Uvicorn process with SQLite and a new guest per size; its first import includes cold TShark field discovery, contributing to small-capture p95. Subsequent requests use cached field selection. HTTP includes request reading, validation, parser, both C++ invocations, pseudonymization, database save and JSON response. No TestClient latency is reported as HTTP latency.

Direct pipeline timing includes Python preprocessing and results. TShark/normalization and each C++ bridge are separately measured in the JSON. C++ bridge timings include process launch, IPC, engine execution and JSON handling; they are not pure in-process CPU time. Full sample lists, p50, nearest-rank p95 and maxima are retained. With seven samples, p95 is the maximum, not a statistically established tail SLO.

| Direct validation workload | Repetitions | Unique cases per execution | p50 ms | p95 ms |
|---|---:|---:|---:|---:|
| single_scenario | 5 | 1 | 1.778 | 3.171 |
| full_plan | 5 | 24 | 740.080 | 770.162 |

Linux maximum RSS reported for reaped child workloads was **175,712 KiB**. This encompasses benchmark child workloads such as TShark/analyzer/API and is not isolated C++ heap, total deployment memory or a leak measurement. LeakSanitizer was disabled for the executed ASan/UBSan checks.
