from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Kind = Literal[
    "beacon",
    "probe_request",
    "probe_response",
    "auth_request",
    "auth_ok",
    "auth_fail",
    "assoc_request",
    "assoc_ok",
    "assoc_reject",
    "deauth",
    "disassoc",
    "data",
    "eapol_1",
    "eapol_2",
    "eapol_3",
    "eapol_4",
    "sae_commit",
    "sae_confirm",
    "dhcp_discover",
    "dhcp_offer",
    "dhcp_request",
    "dhcp_ack",
    "dhcp_fail",
    "dns_query",
    "dns_ok",
    "dns_fail",
    "controller_update",
]
ID = r"^[A-Za-z0-9_.:-]{1,80}$"


class WirelessEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(pattern=ID)
    timestamp_us: int = Field(ge=0, le=9_000_000_000_000_000)
    capture_timestamp: str | None = Field(
        default=None, max_length=40, pattern=r"^\d{1,16}(\.\d{1,12})?$"
    )
    client: str = Field(pattern=ID)
    ap: str = Field(pattern=ID)
    kind: Kind
    code: int = Field(default=-1, ge=-1, le=65535)
    sequence: int = Field(default=-1, ge=-1, le=65535)
    origin: Literal["packet", "synthetic", "ap", "client", "controller"] = "synthetic"
    direction: Literal["ap_to_client", "client_to_ap", "unknown"] = "unknown"
    reported_state: Literal["connected", "disconnected", "unknown"] = "unknown"
    ssid: str | None = Field(default=None, max_length=64)
    frame_subtype: str | None = Field(default=None, max_length=32)
    link_layer: Literal["ieee80211", "ethernet", "synthetic"] = "synthetic"
    missing_fields: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_status(self):
        if self.kind in ("auth_ok", "assoc_ok") and self.code > 0:
            raise ValueError("Successful event cannot contain a rejection status")
        if self.kind in ("auth_fail", "assoc_reject") and self.code <= 0:
            raise ValueError("Explicit rejection requires a nonzero status")
        return self


EXPLANATIONS = {
    "beacon": "AP advertises a network; this does not prove that a client connected.",
    "probe_request": "Client searches for nearby networks.",
    "probe_response": "AP replies to discovery.",
    "auth_request": "802.11 authentication exchange begins; this is not necessarily password validation.",
    "auth_ok": "Successful authentication response observed; association is a separate step.",
    "auth_fail": "Nonzero authentication status is observed; no password cause is inferred.",
    "assoc_request": "Client requests association with an AP.",
    "assoc_ok": "AP accepts association; IP configuration is not implied.",
    "assoc_reject": "AP rejects association with a nonzero status.",
    "deauth": "Authentication relationship terminated; inspect the reason code.",
    "disassoc": "Association terminated; inspect the reason code.",
    "data": "An 802.11 data frame was observed; payload is not inspected.",
    "sae_commit": "SAE commit-stage event/header evidence; no cryptographic verification.",
    "sae_confirm": "SAE confirm-stage event/header evidence; key establishment remains separate.",
    "dhcp_ack": "DHCP ACK evidence indicates IP configuration, not RF quality.",
    "dhcp_fail": "Explicit NAK or a labeled synthetic DHCP timeout.",
    "dns_fail": "DNS response error or a labeled synthetic DNS failure.",
    "dns_ok": "Successful DNS response evidence.",
    "controller_update": "Simulated management-plane observation, not a Cisco API.",
}


def explain(event):
    if event.kind.startswith("eapol_"):
        return f"EAPOL-Key message {event.kind[-1]} observation; MIC/key validity is not verified."
    return EXPLANATIONS.get(
        event.kind,
        "Protocol-stage evidence only; absent packets do not prove a failure.",
    )
