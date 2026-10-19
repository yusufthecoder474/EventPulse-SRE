# WirelessLab

Independent offline wireless feature-validation extension to EventPulse-SRE. Start with [architecture](../docs/WIRELESS_ARCHITECTURE.md), [test plan](../docs/WIRELESS_TEST_PLAN.md), [results](../docs/WIRELESS_TEST_RESULTS.md), [PCAP scope](../docs/PCAP_ANALYSIS.md), and [security](../docs/WIRELESS_SECURITY.md).

Build: `cmake -S wireless-lab/cpp -B wireless-lab/cpp/build -DCMAKE_BUILD_TYPE=Release`, then `cmake --build wireless-lab/cpp/build -j2`. Install backend requirements and TShark, then `python wireless-lab/scripts/run_scenarios.py`. The C++ analyzer can run independently with validated ten-column TSV on stdin; Python provides the JSON contract and orchestration. See architecture for the exact schema. No hardware or AWS account is required.
