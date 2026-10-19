# IEEE 802.11 fundamentals

IEEE 802.11 defines wireless LAN MAC/PHY behavior. An AP joins wireless stations to a distribution network. A controller coordinates AP configuration and management; this project models only management observations.

| Frame / event | What it establishes | What it cannot establish alone |
|---|---|---|
| Beacon | Network advertisement / SSID where present | A client connection |
| Probe request/response | Discovery exchange | Authentication or association |
| Authentication request/response | 802.11 authentication status | Correct password in every security mode |
| Association request/response | Request and explicit AP acceptance/rejection | IP address or internet access |
| Deauthentication/disassociation | Explicit relationship termination and reason code | The ultimate RF/software cause |
| Data | Observed wireless data frame | Payload correctness or IP connectivity |
| EAPOL-Key | Identifiable key-establishment message observations | Valid keys, MICs or completed cryptography |

A common WPA2 personal path is discovery, Open System authentication, association, four-way EAPOL exchange, DHCP and DNS. WPA3 personal uses SAE authentication before association, followed by key establishment; SAE is not the four-way handshake. Enterprise 802.1X/EAP authentication requires additional state that this small model does not implement.

The UI shows status/reason integers with protocol explanations. Zero status means acceptance, nonzero status an explicit rejection; missing status is unknown. A reason such as 3 (leaving) is evidence of the reported reason, not proof of why the client left. The fixtures use association rejection status 17 and authentication rejection 13 as educational examples; the analyzer never infers a wrong password from either.

802.11 data SA/DA may refer to wired hosts; the extractor uses BSSID and transmitter/receiver when available to identify the wireless station. Ethernet EAPOL does not provide an 802.11 BSSID or prove radio association. Discovery-only events are visible but do not create invented client sessions.

References: [IEEE 802.11 working group](https://www.ieee802.org/11/abt80211.html), [Wireshark WLAN fields](https://www.wireshark.org/docs/dfref/w/wlan.html).
