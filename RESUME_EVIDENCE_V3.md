# Cisco replacement project text — preserve existing resume layout

Use only the replacement bullets and skills text below. No resume document, section order, typography or one-page layout was changed.

- Extended a C++17 IEEE 802.11 investigation engine with replay-aware WPA2 header-sequence correlation, missing-stage and timeout classification; verified 39 CTest cases under Release and AddressSanitizer/UBSan builds.
- Built Python/TShark PCAP/PCAPNG import with MAC/SSID pseudonymization and a 24-case wireless validation plan; matched 120/120 held-out synthetic handshake variants and reproduced all registered expected outcomes.
- Integrated guest-isolated React/FastAPI packet investigation and simulated client/AP/controller state comparison; passed 132 Python/API tests, six frontend tests and six real browser flows, with a documented local PostgreSQL skip.

**Evidence:** [Test results](docs/wirelesslab-v3/TEST_RESULTS.md), [CTest](wireless-lab/evidence/v3/cpp-junit.xml), [sanitizers](wireless-lab/evidence/v3/sanitizer-junit.xml), [plan](wireless-lab/evidence/v3/plan-results.json), [held-out evaluation](wireless-lab/evidence/v3/heldout-results.json), [API](wireless-lab/evidence/v3/python-api-junit.xml), [browser](wireless-lab/evidence/v3/browser-junit.xml). CI counts are added only after the full run completes. The 24 unique scenarios and 120 held-out input variants are separate measures; neither is real-world wireless accuracy.

**ATS-friendly skills replacement:** C++17, Python, TypeScript, OOP, STL, RAII, CMake/CTest, IEEE 802.11 fundamentals, WPA2 EAPOL header-sequence analysis, Wireshark/TShark (CLI packet analysis), FastAPI, React, SQLAlchemy, PostgreSQL/SQLite, pytest, Vitest, Playwright, AddressSanitizer/UBSan, Docker Compose, GitHub Actions CI.

No C firmware, device drivers, Cisco hardware, real WLC/CAPWAP, cloud-managed networking, production deployment, genuine capture validation, WPA3 interoperability or cryptographic authentication verification is claimed. Actual Wireshark GUI/adapter capture and native Windows/MSVC testing remain pending. Performance numbers are deliberately left out of these bullets; narrow development measurements are in PERFORMANCE.md.
