# Offline packet analysis

> Initial WirelessLab release guide retained as historical context. For current V3 import/handshake/test-plan capabilities and boundaries, see [V3 architecture](wirelesslab-v3/ARCHITECTURE.md) and [V3 results](wirelesslab-v3/TEST_RESULTS.md). The legacy operator-only `/uploads` remains restricted; V3 adds a separate consent-bound `/imports` endpoint.

Install TShark from your platform's official Wireshark distribution and ensure `tshark --version` works. Build C++ and install backend dependencies first (README). Run `python wireless-lab/scripts/run_scenarios.py --scenario A`. It reads an approved file, calls real TShark, normalizes events, invokes C++ and writes timestamped JSON without overwriting past reports.

## Supported fields and limits

Field availability is discovered with `tshark -G fields`; unsupported extractor fields are returned as metadata. The selection is defined in `packets.py`: frame number/time; WLAN subtype, SA/DA, TA/RA, BSSID, SSID, authentication algorithm/sequence, status/reason and sequence; Ethernet addresses; EAPOL type and `wlan_rsna_eapol.keydes.msgnr`; DHCP message type/client hardware address; DNS response/rcode. No DNS names, IP payloads, key data or packet passwords are extracted.

Supported management subtypes: association request/response, probe request/response, beacon, authentication, disassociation and deauthentication. Reassociation and complete enterprise EAP state are outside this release. Supported data subtypes are 0x20–0x2f. SAE recognizes authentication algorithm 3 and sequence 1/2 as stage observations, without validating group elements or confirms. DHCP Discover/Offer/Request/ACK/NAK and DNS query/response-error observations are supported when cleartext evidence exists. The DHCP/DNS required scenarios deliberately use JSON events; no real packet performance is claimed for those scenarios.

Input requires a plain .pcap/.pcapng filename, recognized magic, <=1 MiB and <=5000 frames. Extraction invokes an argument list with `shell=False`, `-n`, `-r`, disabled WLAN decryption and a private temporary configuration. Timeout is 12 seconds after cached field discovery (10 seconds on first query). Parser output is capped at 4 MB after process completion. Generated PCAPs are radiotap/802.11; a separate Ethernet EAPOL fixture proves the layer distinction. No interfaces, live traffic or `dumpcap` capabilities are used.

## Privacy and exports

Default local-operator ingestion randomizes MAC/SSID pseudonyms per file. Raw packet bytes exist only in the temporary directory, deleted on completion; sanitized metadata/results are saved under the operator's guest ownership. Approved generated fixtures retain their known synthetic identifiers. JSON investigation export includes events, original timestamps, analysis, missing fields, origin, assertions and limitations; CSV is a smaller event table. Guests can download only whitelisted generated PCAP fixtures, not upload files or choose paths.

## Wireshark workflow

Open `wireless-lab/fixtures/association-rejected.pcap` locally. Display-filter `wlan.fc.type_subtype == 0x01` to inspect the response; then `wlan.fixed.status_code != 0` to locate explicit rejection evidence. `eapol` selects key exchanges; `dhcp` and `dns.flags.rcode != 0` are useful in separately authorized cleartext lab traces. A display filter hides rows, while a capture filter determines collection and is not used here. Missing frames can reflect capture position, loss or unsupported fields, so scenario I stays incomplete.

References: [TShark manual](https://www.wireshark.org/docs/man-pages/tshark.html), [WLAN fields](https://www.wireshark.org/docs/dfref/w/wlan.html), [EAPOL-Key fields](https://www.wireshark.org/docs/dfref/w/wlan_rsna_eapol.html), [DHCP](https://www.wireshark.org/docs/dfref/d/dhcp.html), [DNS](https://www.wireshark.org/docs/dfref/d/dns.html).
