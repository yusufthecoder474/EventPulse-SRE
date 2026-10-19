# Explicit validation boundaries

- No genuine authorized network capture was supplied. Import was exercised with generated PCAP and PCAPNG; unknown origins remain user_supplied_unverified. Real-world capture verification is pending.
- No physical AP, Cisco equipment, CAPWAP, enterprise controller, cloud-managed deployment, driver, firmware, RF or production validation.
- WPA2 classifications concern observed key headers/roles/replay/chronology; no MIC, nonce, key installation, credential correctness, PSK policy, decryption or cryptographic verification. EAPOL alone can occur in enterprise contexts.
- WPA3/SAE remains conceptual/previous event fixtures only, not WPA2 renamed as WPA3 and not interoperability testing.
- Ordinary Ethernet-style Wi-Fi captures may lack management evidence. Empty or mid-session captures cannot establish a complete connection or unseen failure cause. Encrypted payloads remain opaque.
- PCAP v2.4 and enhanced-packet PCAPNG v1.0 subset only; three link types. Simple/legacy PCAPNG packet blocks, decryption-secret blocks and unsupported link layers are rejected clearly. MAC/SSID pseudonyms change per import, preventing cross-file identity correlation by design.
- Replay counters are not universally unique session identifiers. Multiple ambiguous attempts remain insufficient; equivalent metadata is only a possible retransmission. More than 64 active attempts for one pair is rejected. Complete stage sets must also satisfy the modeled ordering/flags/counters.
- Controller/client/dashboard states are small common-clock simulations. Missing observation is not proof of failed transport or device behavior; no complete eventual-consistency or multi-session controller implementation.
- API quotas/concurrency gates target the shipped single worker; native parser subprocess limits do not provide full sandbox isolation. Keep all analysis local and authorized.
- Local testing uses Linux/GCC; native PostgreSQL was unavailable locally and its test is explicitly skipped. Real CI is used for Docker/PostgreSQL/monitoring/recovery. Windows/MSVC and ThreadSanitizer are not claimed. LeakSanitizer was disabled during ASan/UBSan checks.
- Performance is development-container synthetic workload timing. Seven samples produce p95 equal to max; no production SLO, Cisco scale or language comparison is inferred. RSS represents child-workload peaks, not isolated C++ heap.
- All resume metrics are tied to named test/evaluation reports. Held-out data varies the same scenario families and does not estimate real-world accuracy.
