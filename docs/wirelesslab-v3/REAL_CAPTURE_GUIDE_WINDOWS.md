# Windows: local demonstration and authorized capture guide

Install Git, Python 3.12, Docker Desktop with Linux containers and Node 22+ if using native frontend tools. Start Docker Desktop first. No AWS or paid service is required. Commands below are PowerShell, from a directory where you keep projects:

```powershell
git clone --branch feature/wirelesslab-v3-cisco-validation https://github.com/yusufthecoder474/EventPulse-SRE.git
Set-Location EventPulse-SRE
py -3.12 scripts/bootstrap.py
docker compose config --quiet
docker compose up --build -d --wait
docker compose ps
Start-Process 'http://localhost:8080/?lab=wireless'
```

Bootstrap creates ignored local environment values only when needed; preserve your existing `.env`. For an existing checkout with unrelated edits, keep those edits and use a separate clone instead of resetting or overwriting files. Main is not modified or merged by this upgrade.

## Recruiter walkthrough (hardware-free)

1. Open the URL and choose **Continue as Guest**. No email, password, OTP or signup.
2. Open **Automated test scenarios**, leave the V3 selector on the full 24-case plan and click **Run selected validation plan**. Read four separate counters; a passing rejection is an expected negative test.
3. Choose C02 and run it, then open **Failure investigation**. Show disconnected AP/client versus stale connected controller/dashboard. Explain that every device view is simulated.
4. Open **Packet trace explorer**, select `wireless-lab\fixtures\v3\ethernet-eapol.pcapng`, confirm authorization for this generated fixture, and analyze. Read format, packet count and the explicit missing 802.11 management warning.
5. Open **Failure investigation** and show M1–M4 packet IDs/replay counters. Explain that complete observed headers are not a cryptographic success claim. Export sanitized JSON and test-plan CSV/JSON. **End demo** removes the guest's stored rows.

SRE UI remains at `http://localhost:8080/`; API docs at `http://localhost:8000/docs`; Grafana at `http://localhost:3000` using your locally generated credentials. Never paste `.env` values into screenshots or GitHub. `docker compose down` stops this project; do not add `-v` unless you explicitly intend to delete its database volumes.

## Capturing on your own authorized network (optional, manual)

No genuine capture was supplied for this release. Real-capture verification remains pending. Install official Wireshark with the supported Npcap options for your own machine, then check adapter capabilities. An ordinary Windows Wi-Fi capture often presents Ethernet-style packets and will not prove radio association/authentication. Monitor-mode support depends on adapter/driver/capture environment; do not assume it, enable it blindly, disconnect the real network, or inject frames.

Use only an isolated network and devices you own or have explicit permission to analyze. Close unrelated applications. The following optional commands capture locally; WirelessLab itself never runs them:

```powershell
& "$env:ProgramFiles\Wireshark\tshark.exe" -D
$AdapterId = Read-Host 'Enter the interface number for your authorized lab adapter'
& "$env:ProgramFiles\Wireshark\tshark.exe" -i $AdapterId -p -a duration:15 -a filesize:512 -c 500 -w .\authorized-lab.pcapng
```

This sets a short duration/count/size limit and does not request monitor mode or decryption. Inspect the file locally in Wireshark first; remove unrelated/private data and do not embed decryption secrets. Import it through Packet trace explorer only if authorized. Never upload it to GitHub or an external analysis service. Missing management-layer evidence is an expected limitation on ordinary interfaces. Capturing encrypted application traffic will not automatically expose DHCP/DNS or earlier join stages.

Native C++ testing without Docker requires CMake and Visual Studio Desktop C++ Build Tools:

```powershell
cmake -S wireless-lab/cpp -B wireless-lab/cpp/build
cmake --build wireless-lab/cpp/build --config Release
$env:WIRELESS_ANALYZER = (Resolve-Path wireless-lab/cpp/build/Release/wireless_analyzer.exe).Path
ctest --test-dir wireless-lab/cpp/build -C Release --output-on-failure
```

The benchmark script currently uses Linux `/proc` and resource RSS semantics; run it inside a suitable Linux environment, not unmodified native Windows. These Windows instructions are documented, not an executed MSVC/Windows test result. [Official Wireshark WLAN capture guidance](https://wiki.wireshark.org/CaptureSetup/WLAN).
