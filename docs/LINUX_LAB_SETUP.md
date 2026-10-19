# Linux optional virtual radio evaluation

Offline mode is the supported release path. This development container has no `iw`, `hostapd` or `wpa_supplicant`, and no usable host-kernel mac80211_hwsim module exposed to it. No virtual radios were created. No privileged command, module load, network namespace, interface change or live capture was attempted. Native host support is **not verified**. Docker builds do not provide radio emulation or a replacement kernel.

On a separately authorized native Linux lab, an operator may first inspect `uname -r`, `command -v iw hostapd wpa_supplicant tshark`, and `modinfo mac80211_hwsim` without changing interfaces. A future integration needs isolated simulated radios, explicit interface ownership, protected namespaces, a dedicated SSID, lifecycle cleanup, controlled WPA2/SAE settings and packet evidence. Request approval before any module loading or privileged network operation. Do not run against the machine's real Wi-Fi device or main network.

WSL2 and Docker Desktop must not be assumed to ship the required kernel module. Keep using the offline generated fixtures when support is missing. Linux-only integration, real WPA3 and physical AP/controller compatibility remain pending.
