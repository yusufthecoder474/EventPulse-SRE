# V3 security review

The new `/imports` capability is separately authorized file parsing under the existing guest cookie, custom mutation header, same-origin allowlist and explicit authorization declaration. It does not grant the operator-only `/uploads` secret or expose OS/network commands. No packet is transmitted or captured by the application. File bytes are sent only to the same local backend; none are sent to an external analysis service.

| Area | Implemented control / verification |
|---|---|
| File/path input | Plain PCAP/PCAPNG filename only; private randomized temporary directory; no path/command interpolation |
| Container validity | Strict magic/version/record/block/length/interface checks; only three supported link types; secret blocks rejected |
| Resource bounds | 1 MiB, 5000 packets, ten-second body-read timeout; four shared execution slots; 12 expensive operations/minute/session |
| Native tools | TShark argument list with shell=False, disabled WLAN decryption and private config; 10-second first discovery, 12-second parse, eight-second C++ invocation limits |
| C++ | <=50000 records, uint64 counters, <=64 active attempts/pair, value ownership and bounded IDs; executed ASan/UBSan (leak detection off) |
| Guest isolation | Existing random HttpOnly/SameSite cookie and hash-only database ownership; foreign reads/exports return 404; tests cover capture/plan isolation and logout |
| Storage/cleanup | Raw temporary files removed after extraction; only normalized pseudonymized metadata saved; twenty retained runs; lazy expiry cleanup and logout removal |
| Sensitive content | No payload, DNS name, IP, nonce, MIC or key extraction; per-file MAC/SSID pseudonyms in imports; filenames not retained in reports |
| Exports/logs/metrics | Owner-scoped JSON/CSV; validated identifiers/registry text; audit IDs and finite metric labels, no guest tokens or file payloads |

Cookie Secure follows HTTPS scheme as before; a real reverse-proxy deployment must handle trusted proxy/HTTPS correctly. Local HTTP Compose is a laboratory demo, not a public-production security claim. Incoming headers and raw bytes must not be logged by a future proxy. Pseudonymized metadata can still be sensitive; server operators can access its database and backups. Guest isolation is application authorization, not cryptographic encryption against the server owner.

Limits are not an OS memory sandbox: subprocess output is checked after completion, and worker-thread cancellation is not a subprocess kill. Container parsing is bounded but TShark remains a complex native parser; keep it patched, run nonroot without capture privileges, and do not publish the development server or enable privileged networking. PCAPNG support is intentionally a strict subset. A public multi-worker deployment would need shared admission/quotas and stronger per-process CPU/memory containment. The shipped application remains one worker, unchanged from baseline.

Legacy `/uploads` remains restricted; it is not the public import path and has its historical operator bounds. Real captures were not supplied, no adversarial production penetration test was conducted, and no hardware/security certification is implied. Negative tests exercise malformed/truncated formats, path traversal, payload size, missing consent/session, quotas, foreign exports and unsupported link types. Full scan JSONs are in `wireless-lab/evidence/v3/`; unresolved dependency advisories are reported, not hidden. Current exact counts are recorded with TEST_RESULTS.md after scans complete.
