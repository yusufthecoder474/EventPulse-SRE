# Capture format and protocol evidence

Supported containers: PCAP v2.4 (both byte orders, microsecond/nanosecond timestamps) and PCAPNG v1.0 sections/interfaces/enhanced-packet blocks. TShark is the maintained protocol decoder. Header preflight rejects corrupt/truncated blocks/records before extraction, unknown interface references, oversized packet lengths, excessive counts and unsupported link types. Supported link types are 1 Ethernet, 105 raw IEEE 802.11 and 127 radiotap/802.11. Legacy/simple PCAPNG packet blocks without supported timing, decryption-secret blocks and unsupported link types return a clear error; this release intentionally supports a bounded subset.

Capture metadata reports format, link types, total container packet count (including packets without supported protocol events), duration, timestamp range, and physical timestamp disorder. Original decimal capture timestamps remain in events; integer microseconds drive correlation. Unknown user files are `user_supplied_unverified`; only exact checksums in the synthetic manifests get `synthetic_generated`. No content-based claim of genuine origin is made. All verification fixtures supplied in this release are synthetic.

The protocol allowlist includes beacon/probe/authentication/association/deauth/disassoc, 802.11 data, EAPOL header metadata, DHCP message type/client hardware address, and DNS response/rcode. It excludes payload content, names queried in DNS, IP addresses, nonces, MICs and keys. Reassociation, full 802.1X and encrypted DHCP/DNS decoding are outside scope. WLAN TA/RA and BSSID identify the wireless station when present; SA/DA alone may refer to wired hosts.

Ethernet EAPOL can establish an authenticator/supplicant observation without radio management evidence. The association analyzer keeps AP context unknown for Ethernet. Captures with no management frames display the exact warning:

> 802.11 management-layer evidence unavailable in this capture.

An ordinary IP-only Ethernet capture is accepted with an empty supported-event table and this warning, not classified as a failed association. Empty supported-format captures similarly return no invented session. The UI shows metadata, a sortable/filterable packet-level table and protocol/handshake timelines with packet references. JSON exports preserve metadata, warnings, stage reasoning and pseudonyms; event CSV remains compatible with prior consumers.

Key-frame numbering uses Key Information pairwise/ACK/MIC/install/secure flags. This avoids treating packet position as protocol identity and resolves the generated zero-key-data M2 packet's ambiguous TShark message-number heuristic. It does not validate the synthetic payload cryptographically.

References: [Wireshark WLAN fields](https://www.wireshark.org/docs/dfref/w/wlan.html), [RSNA EAPOL fields](https://www.wireshark.org/docs/dfref/w/wlan_rsna_eapol.html), [EAPOL replay counter and descriptor](https://www.wireshark.org/docs/dfref/e/eapol.html), [TShark manual](https://www.wireshark.org/docs/man-pages/tshark.html), [PCAPNG format](https://wiki.wireshark.org/Development/PcapNg/).
