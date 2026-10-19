# WPA2 / WPA3 observation scope

> Initial WirelessLab release guide retained as historical context. For current V3 import/handshake/test-plan capabilities and boundaries, see [V3 architecture](wirelesslab-v3/ARCHITECTURE.md) and [V3 results](wirelesslab-v3/TEST_RESULTS.md). The legacy operator-only `/uploads` remains restricted; V3 adds a separate consent-bound `/imports` endpoint.

WPA2 personal commonly performs Open System 802.11 authentication and association before the four-way EAPOL-Key exchange. That exchange establishes session keys from existing key material. Counting messages does not authenticate the cryptographic transcript. `association-success.pcap` contains four deliberately generated EAPOL-Key structures with zero placeholder nonce/MIC/key data; no usable credentials or working encrypted connection are demonstrated.

The analyzer reports the observed message numbers and `four_messages_observed_not_cryptographically_verified` only when all four message types occur. This is a set-based completeness observation, not replay-counter, message-order, retransmission or MIC verification. Missing messages are `incomplete_or_not_captured`, not proof of an incorrect password. Ethernet-only EAPOL remains incomplete at the radio association layer.

WPA3 personal uses SAE: commit and confirm exchanges authenticate peers before association. Subsequent EAPOL key establishment remains a separate stage. The extractor recognizes suitable SAE authentication headers when available; JSON `wpa3-sae-events.json` tests bidirectional commit/confirm event transitions and successful association without pretending that EAPOL was captured. Neither SAE payload cryptography nor anti-clogging, roaming, PMF policy or interoperability is validated.

Full WPA3 integration and all WPA2/WPA3 hardware testing are **pending**. No Cisco hardware, radio, firmware, credentials, decryption or attacks were used.

References: [Microsoft SAE authentication](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/wpa3-sae-authentication), [Cisco WPA3 overview](https://www.cisco.com/c/en/us/td/docs/wireless/controller/9800/26-1/configuration-guide/wl-26-1-cg/wpa3/overview-of-wpa3.html), [Wireshark WLAN reference](https://www.wireshark.org/docs/dfref/w/wlan.html).
