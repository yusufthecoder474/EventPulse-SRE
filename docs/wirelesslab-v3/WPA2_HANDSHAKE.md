# Defensive WPA2 handshake observation

Scope is a WPA2-Personal-style pairwise CCMP four-message transcript: descriptor type 2, key version 2, known pairwise/ACK/MIC/install/secure flags, directions, timestamps and replay counters. EAPOL headers alone cannot prove the negotiated PSK/security policy without RSN context; enterprise exchanges can share this structure. No passwords, nonces, MIC bytes, recovered keys or cryptographic verification are used. HANDSHAKE_COMPLETE means complete **header-consistent observed evidence**, not working encryption or verified authentication.

| Stage | Expected header/role evidence |
|---|---|
| M1 | Authenticator→client, pairwise ACK without MIC; initial replay counter |
| M2 | Client→authenticator, pairwise MIC without secure; same counter as M1 |
| M3 | Authenticator→client, ACK/MIC/install; counter greater than M1 (not assumed exactly +1) |
| M4 | Client→authenticator, MIC/secure; same counter as M3 |

Sessions are indexed by client/authenticator, M1 replay epoch and time window. Different M1 counters create distinct attempts. M2 matches the initial counter; M3/M4 match available consistent candidate context. Ambiguous candidates are flagged insufficient rather than forcibly joined. Metadata-equivalent repeated message/counter observations count as possible retransmissions; nonce/payload equality is not inspected, so equal-counter reauthentication cannot always be distinguished from retransmission. The model rejects >64 active attempts for one pair.

Stable timestamp sorting corrects physical arrival disorder. A later timestamp for an unseen earlier stage after a later stage yields UNEXPECTED_SEQUENCE; merely reordering the input array does not. An absent stage yields HANDSHAKE_INCOMPLETE. Missing roles/unsupported flags/descriptor/counter or ambiguous grouping yields INSUFFICIENT_EVIDENCE. HANDSHAKE_TIMEOUT requires an incomplete session and an observed capture interval extending at least the configured 5000 ms window (500–60000 configurable); it describes a completion-window observation, not a proven internal client timeout or wrong password. Missing M1 alone is not a credential diagnosis.

P01–P10 cover complete, each missing message, reordered stages, retransmission, timeout, insufficient capture and concurrent clients. Eighteen added CTest cases cover these and malformed/duplicate/ambiguous input, uint64 boundary, empty input, timestamp disorder, replay mismatch and a bounded 10,000-event case. Separate held-out synthetic variants vary timestamps, gaps, replay deltas, identities, order and retries with seed 73129; exact input/hash and results are committed. These were not used as development fixture files, but are generated from the same scenario families: this is not independent real-world or cryptographic accuracy.

WPA3/SAE remains conceptual and the prior fixture-stage observations remain labeled as such. No WPA2 result is described as WPA3 interoperability. [Official Wireshark header fields](https://www.wireshark.org/docs/dfref/w/wlan_rsna_eapol.html).
