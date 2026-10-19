# Cisco wireless interview practice

Answers describe implemented and tested scope; do not imply hardware integration.

## 1. What is IEEE 802.11?

**Simple explanation:** The family of standards describing wireless LAN link behavior, including discovery, authentication, association and data transfer.

**Example:** A laptop sees a network advertisement before joining.

**Project:** Beacon/probe/authentication/association parsing in packets.py and the protocol-stage timeline.

**Likely follow-up:** Which parts are MAC versus PHY? The project examines decoded MAC-level events and does not model RF/PHY.

## 2. What is the difference between an AP and a controller?

**Simple explanation:** An AP provides the wireless link; a controller coordinates management across APs.

**Example:** An AP disconnects a station while the central dashboard still shows connected.

**Project:** Scenario J compares AP state and a delayed synthetic controller update.

**Likely follow-up:** Does this call a Cisco controller? No, it is a simplified event model without vendor compatibility.

## 3. How does a Wi-Fi client connect?

**Simple explanation:** Typically discovery, authentication, association, key establishment, then IP configuration and name resolution. Security mode changes details.

**Example:** A phone joins the SSID but DHCP fails, so applications still cannot communicate normally.

**Project:** Scenario A covers packet-level association; E and F model later IP/DNS stages.

**Likely follow-up:** Does successful association prove internet access? No; those are separate layers.

## 4. Authentication versus association?

**Simple explanation:** Authentication establishes the authentication relationship; association accepts the station into the AP link context. Neither alone proves encrypted data works.

**Example:** An AP accepts Open System authentication but rejects association because of a policy or capacity condition.

**Project:** Separate auth_ok/auth_fail and assoc_ok/assoc_reject transitions; scenario B.

**Likely follow-up:** Does authentication always validate the password? No; Open System authentication does not.

## 5. WPA2 versus WPA3?

**Simple explanation:** WPA2 personal commonly uses a shared-secret-derived key path; WPA3 personal uses SAE authentication, followed by key establishment. Complete security properties require real cryptographic testing.

**Example:** A WPA3-only network needs SAE-capable peers.

**Project:** Bidirectional synthetic SAE events are separate from EAPOL observations.

**Likely follow-up:** Was WPA3 tested on hardware? No; fixture validation only, with full integration pending.

## 6. Why is EAPOL important?

**Simple explanation:** It carries authentication/key-establishment traffic, including recognizable four-way handshake evidence. Seeing messages does not verify keys or MICs.

**Example:** A trace has M1 and M2 but not M3/M4; missing capture context must be considered.

**Project:** C++ records observed EAPOL message numbers; generated zero-placeholder fixtures carry no valid credential exchange.

**Likely follow-up:** Why not say the handshake succeeded? This analyzer does not verify transcript order, MICs or key installation.

## 7. How does DHCP work after joining?

**Simple explanation:** A typical DHCPv4 sequence is Discover, Offer, Request, ACK, providing an IP configuration after link access.

**Example:** A station associates but a lease server returns a NAK or an explicit lab timeout occurs.

**Project:** Scenario E is labeled synthetic and classifies dhcp_failed separately from association.

**Likely follow-up:** Can a missing ACK prove DHCP failure? No; missing capture evidence alone is insufficient.

## 8. Why can DNS fail while Wi-Fi is connected?

**Simple explanation:** Link connectivity and an IP address do not guarantee a reachable or correctly answering DNS resolver.

**Example:** A browser cannot resolve a hostname because the resolver returns an error.

**Project:** Scenario F includes successful IP configuration then a synthetic DNS error.

**Likely follow-up:** Would you reset the AP first? Inspect the DNS evidence and resolver path before assigning an RF cause.

## 9. What does a packet capture contain?

**Simple explanation:** Recorded frames plus timestamps and capture/link metadata, depending on capture position and format. It may omit important stages and contain sensitive content.

**Example:** A capture started after joining contains only data, not the original association.

**Project:** PCAP ingestion preserves decimal timestamp text, extracts allowlisted metadata and records missing fields.

**Likely follow-up:** Does Ethernet EAPOL prove radio association? No; the dedicated fixture remains incomplete for 802.11 context.

## 10. How do Wireshark filters work?

**Simple explanation:** Display filters select decoded rows for inspection; capture filters restrict collection earlier. This project uses offline extraction only.

**Example:** Filter wlan.fc.type_subtype == 0x01 to examine association responses.

**Project:** PCAP_ANALYSIS documents display filters and the UI filters normalized event rows.

**Likely follow-up:** Does a UI text filter change the capture? No; it changes visible normalized rows only.

## 11. How do you debug a failed association?

**Simple explanation:** Find the last established protocol stage, inspect explicit response status, correlate nearby evidence, and keep unobserved causes unknown.

**Example:** Association response status 17 identifies rejection, but not a demonstrated password failure.

**Project:** Scenario B, C++ priority classification and Failure investigation view.

**Likely follow-up:** How would AP/client clocks affect correlation? Clock skew can create incorrect lag; this lab assumes a common clock.

## 12. How do you automate wireless scenarios?

**Simple explanation:** Declare fixtures and expected outcomes, execute the real pipeline, compare assertions and preserve actual evidence.

**Example:** A negative test passes when an AP rejection is correctly reproduced and classified.

**Project:** catalog.json, run_scenarios.py and timestamped JSON evidence for A–J.

**Likely follow-up:** Could a passing fixture suite prove field reliability? No; coverage is limited to designed inputs.

## 13. Why use C++?

**Simple explanation:** To implement explicit state tracking, bounded parsing, ordered correlation and deterministic analysis in a separately testable systems component.

**Example:** Ten thousand normalized records are sorted and deduplicated before per-client analysis.

**Project:** Analyzer class, vector/map/set containers, RAII, CMake and 21 CTest cases.

**Likely follow-up:** Is this firmware or a performance comparison against Python? Neither; only the implemented pipeline is measured.

## 14. Why use Python?

**Simple explanation:** It is convenient for subprocess orchestration, schema validation, fixture automation, API integration and reports.

**Example:** Python extracts TShark fields, validates events and sends safe TSV to C++.

**Project:** packets.py, schema.py, analyze.py and scenario runner.

**Likely follow-up:** Why TSV internally? It keeps the C++ parser small; metadata remains in JSON outside the ten-column validated boundary.

## 15. How does the dashboard communicate with the backend?

**Simple explanation:** Same-origin HTTP through the existing /api proxy, with a server-issued HttpOnly guest cookie and typed JSON responses.

**Example:** Click Run scenario B, store its result under that guest, then load event and investigation views.

**Project:** WirelessLab.tsx uses FastAPI guest/run/history/export routes.

**Likely follow-up:** How is cross-guest access prevented? Every saved row has an owner checked server-side; another session sees 404.

## 16. What can you validate without hardware?

**Simple explanation:** Parser correctness, deterministic state transitions, designed failure classifications, safe APIs and UI behavior. RF behavior, real timing and interoperability need a real or supported virtual lab.

**Example:** A generated deauth frame proves decoder/classifier handling, not actual radio disconnect reliability.

**Project:** Fixture provenance, WPA2_WPA3 and LINUX_LAB_SETUP list limits.

**Likely follow-up:** Can mac80211_hwsim replace RF testing? It can validate some software paths but does not recreate real RF conditions.

## 17. What does the simulated controller represent?

**Simple explanation:** A delayed observer of AP state, sufficient to reason about stale management data. It is not a vendor protocol implementation.

**Example:** A connected update arrives after a disconnect and disagrees with the current AP state.

**Project:** controller_update with reported_state, last_ap_change, lag and inconsistency findings.

**Likely follow-up:** Does this model retries, eventual consistency and clock synchronization? Only a small common-clock event window, not a distributed control system.

## 18. How does GitHub Actions verify changes?

**Simple explanation:** It builds C++, executes CTest/Python/frontend/browser checks, runs the existing Compose reliability suite and stores real artifacts.

**Example:** A parser regression can fail a scenario assertion before a PR is merged.

**Project:** Existing ci.yml extended with wireless build, fixtures, scans and reports; no deployment stage added.

**Likely follow-up:** Is a configured workflow a verified run? No; inspect the actual run conclusion and reports.

## 60-second explanation

“I extended my EventPulse reliability platform with WirelessLab to practice wireless feature validation. Python reads approved synthetic packet captures through TShark, normalizes the evidence, and passes validated events to a separate C++17 state analyzer. The analyzer correlates authentication, association and later events per client and AP, handles duplicates and timestamp disorder, and explains explicit failures without guessing missing causes. I built ten reproducible scenarios, from AP rejection to DHCP, DNS and stale controller updates, and integrated them into a FastAPI and React guest demo. Guests can run fixtures, inspect packet timelines and export reports without an account, while their data and quotas are isolated. I tested the C++ transitions, parser/API integration and browser flows and kept the original SRE regression checks. This is offline laboratory validation: I have not claimed Cisco hardware, RF performance, firmware work or WPA3 cryptographic interoperability.”
