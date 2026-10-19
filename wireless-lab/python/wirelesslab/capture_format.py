"""Small strict container preflight; protocol decoding remains with maintained TShark."""

import hashlib
import json
import struct
from pathlib import Path
from decimal import Decimal

SUPPORTED = {1: "ethernet", 105: "ieee80211", 127: "radiotap_ieee80211"}
WARNING = "802.11 management-layer evidence unavailable in this capture."


def inspect_container(data, max_packets=5000):
    if not isinstance(data, bytes) or not 24 <= len(data) <= 1048576:
        raise ValueError("Capture must be 24 bytes..1 MiB")
    packets = []
    links = set()

    def packet(ts, caplen, original, link):
        if caplen > original or original > 16_777_216:
            raise ValueError("Invalid packet lengths")
        if len(packets) >= max_packets:
            raise ValueError("Capture exceeds 5000-packet limit")
        links.add(link)
        packets.append((ts, caplen))

    magic = data[:4]
    variants = {
        b"\xd4\xc3\xb2\xa1": ("<", 1000000),
        b"\xa1\xb2\xc3\xd4": (">", 1000000),
        b"\x4d\x3c\xb2\xa1": ("<", 1000000000),
        b"\xa1\xb2\x3c\x4d": (">", 1000000000),
    }
    if magic in variants:
        fmt = "pcap"
        endian, scale = variants[magic]
        major, minor = struct.unpack_from(endian + "HH", data, 4)
        snap, link = struct.unpack_from(endian + "II", data, 16)
        if (major, minor) != (2, 4) or not 1 <= snap <= 16777216:
            raise ValueError("Unsupported PCAP header/version")
        link &= 0xFFFF
        links.add(link)
        offset = 24
        while offset < len(data):
            if offset + 16 > len(data):
                raise ValueError("Truncated PCAP record header")
            sec, sub, cap, original = struct.unpack_from(endian + "IIII", data, offset)
            offset += 16
            if sub >= scale or cap > snap or offset + cap > len(data):
                raise ValueError("Truncated or corrupt PCAP record")
            packet(Decimal(sec) + Decimal(sub) / scale, cap, original, link)
            offset += cap
    elif magic == b"\x0a\x0d\x0d\x0a":
        fmt = "pcapng"
        offset = 0
        endian = None
        interfaces = []
        while offset < len(data):
            if offset + 12 > len(data):
                raise ValueError("Truncated PCAPNG block")
            if data[offset : offset + 4] == magic:
                if offset + 28 > len(data):
                    raise ValueError("Truncated PCAPNG section")
                bom = data[offset + 8 : offset + 12]
                endian = {b"\x4d\x3c\x2b\x1a": "<", b"\x1a\x2b\x3c\x4d": ">"}.get(bom)
                if endian is None:
                    raise ValueError("Invalid PCAPNG byte order")
                interfaces = []
            if endian is None:
                raise ValueError("Missing PCAPNG section")
            kind, size = struct.unpack_from(endian + "II", data, offset)
            if (
                size < 12
                or size % 4
                or offset + size > len(data)
                or struct.unpack_from(endian + "I", data, offset + size - 4)[0] != size
            ):
                raise ValueError("Truncated or corrupt PCAPNG block length")
            body = data[offset + 8 : offset + size - 4]
            if kind == 0x0A0D0D0A:
                if len(body) < 16 or struct.unpack_from(endian + "HH", body, 4) != (
                    1,
                    0,
                ):
                    raise ValueError("Unsupported PCAPNG section version")
            elif kind == 1:
                if len(body) < 8:
                    raise ValueError("Invalid PCAPNG interface")
                link, _, snap = struct.unpack_from(endian + "HHI", body)
                if snap > 16777216:
                    raise ValueError("Invalid PCAPNG snapshot length")
                resolution = Decimal("0.000001")
                time_offset = 0
                pos = 8
                while pos < len(body):
                    if pos + 4 > len(body):
                        raise ValueError("Truncated PCAPNG option")
                    code, length = struct.unpack_from(endian + "HH", body, pos)
                    pos += 4
                    if pos + length > len(body):
                        raise ValueError("Truncated PCAPNG option data")
                    value = body[pos : pos + length]
                    pos += (length + 3) // 4 * 4
                    if code == 0:
                        if length:
                            raise ValueError("Invalid PCAPNG end option")
                        break
                    if code == 9:
                        if length != 1 or (value[0] & 127) > 63:
                            raise ValueError("Unsupported timestamp resolution")
                        resolution = Decimal(2 if value[0] & 128 else 10) ** -(
                            value[0] & 127
                        )
                    if code == 14:
                        if length != 8:
                            raise ValueError("Invalid timestamp offset")
                        time_offset = struct.unpack(endian + "q", value)[0]
                interfaces.append((link, snap, resolution, time_offset))
                links.add(link)
            elif kind == 6:
                if len(body) < 20:
                    raise ValueError("Invalid PCAPNG enhanced packet")
                index, high, low, cap, original = struct.unpack_from(
                    endian + "IIIII", body
                )
                if index >= len(interfaces):
                    raise ValueError("Unknown PCAPNG interface")
                link, snap, resolution, time_offset = interfaces[index]
                if (snap and cap > snap) or 20 + (cap + 3) // 4 * 4 > len(body):
                    raise ValueError("Truncated PCAPNG packet data")
                packet(
                    Decimal((high << 32) | low) * resolution + time_offset,
                    cap,
                    original,
                    link,
                )
            elif kind in (2, 3):
                raise ValueError(
                    "Legacy/simple PCAPNG packet blocks lack supported timing; convert to enhanced packets"
                )
            elif kind == 10:
                raise ValueError("PCAPNG decryption-secret blocks are not accepted")
            offset += size
    else:
        raise ValueError("Unsupported capture format; use PCAP or PCAPNG")
    if not links or links - set(SUPPORTED):
        raise ValueError(
            "Unsupported link-layer type; accepted Ethernet, raw 802.11 and radiotap"
        )
    times = [p[0] for p in packets]
    if any(t < 0 or t > Decimal("9000000000") for t in times):
        raise ValueError("Capture timestamp is out of range")
    manifest = Path(__file__).resolve().parents[2] / "fixtures/manifest.json"
    hashes = (
        {x["sha256"] for x in json.loads(manifest.read_text())}
        if manifest.exists()
        else set()
    )
    extra_manifest = manifest.parent / "v3/manifest.json"
    if extra_manifest.exists():
        hashes.update(x["sha256"] for x in json.loads(extra_manifest.read_text()))
    return {
        "format": fmt,
        "link_types": [SUPPORTED[x] for x in sorted(links)],
        "link_type_numbers": sorted(links),
        "packet_count": len(packets),
        "capture_duration_ms": float((max(times) - min(times)) * 1000) if times else 0,
        "first_timestamp": str(min(times)) if times else None,
        "last_timestamp": str(max(times)) if times else None,
        "observed_until_us": int(max(times) * 1000000) if times else 0,
        "container_out_of_order_pairs": sum(
            b[0] < a[0] for a, b in zip(packets, packets[1:])
        ),
        "origin": "synthetic_generated"
        if hashlib.sha256(data).hexdigest() in hashes
        else "user_supplied_unverified",
        "real_capture_validated": False,
    }
