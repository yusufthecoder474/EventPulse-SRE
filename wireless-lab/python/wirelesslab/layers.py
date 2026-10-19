"""Evidence-scoped simulation. Not CAPWAP, a real WLC, or an RF diagnosis."""


def correlate_layers(events, window_ms=5000):
    groups = {}
    for event in sorted(events, key=lambda x: x["timestamp_us"]):
        if event["kind"] not in {
            "assoc_ok",
            "assoc_reject",
            "auth_fail",
            "deauth",
            "disassoc",
            "controller_update",
            "client_update",
            "dashboard_update",
        }:
            continue
        key = (event["client"], event["ap"])
        item = groups.setdefault(
            key,
            {
                "client": key[0],
                "ap": key[1],
                "client_state": "unknown",
                "ap_state": "unknown",
                "controller_state": "unknown",
                "dashboard_state": "unknown",
                "classification": "MISSING_MANAGEMENT_EVIDENCE",
                "hypotheses": [],
                "event_references": [],
                "timeline": [],
                "controller_lag_ms": None,
                "simulated": True,
            },
        )
        kind = event["kind"]
        state = event.get("reported_state", "unknown")
        layer = "ap"
        if kind == "assoc_ok":
            item["ap_state"] = "connected"
            item["_ap_time"] = event["timestamp_us"]
        elif kind in {"deauth", "disassoc", "assoc_reject", "auth_fail"}:
            item["ap_state"] = "disconnected"
            item["_ap_time"] = event["timestamp_us"]
        elif kind == "client_update":
            layer = "client"
            item["client_state"] = state
        elif kind == "controller_update":
            layer = "controller"
            item["controller_state"] = state
            if "_ap_time" in item:
                item["controller_lag_ms"] = (
                    event["timestamp_us"] - item["_ap_time"]
                ) / 1000
        elif kind == "dashboard_update":
            layer = "dashboard"
            item["dashboard_state"] = state
        item["event_references"].append(event["event_id"])
        item["timeline"].append(
            {
                "event_id": event["event_id"],
                "timestamp_us": event["timestamp_us"],
                "layer": layer,
                "state": item.get(layer + "_state", "unknown"),
            }
        )
    for item in groups.values():
        ap, controller, client, dashboard = [
            item[x + "_state"] for x in ["ap", "controller", "client", "dashboard"]
        ]
        if controller == "unknown":
            item["classification"] = "MISSING_MANAGEMENT_EVIDENCE"
            item["hypotheses"] = [
                "No controller observation is present; transport loss or capture omission is unproven."
            ]
        elif (ap != "unknown" and ap != controller) or (
            dashboard != "unknown" and dashboard != controller
        ):
            item["classification"] = "STALE_OR_INCONSISTENT_CONTROLLER"
            item["hypotheses"] = [
                "Observed views disagree; delayed/stale synchronization is a hypothesis, not a proven vendor fault."
            ]
        elif client != "unknown" and ap != "unknown" and client != ap:
            item["classification"] = "CLIENT_AP_MISMATCH"
            item["hypotheses"] = [
                "Client and AP observations disagree; additional logs and synchronized clocks are required."
            ]
        elif (
            item["controller_lag_ms"] is not None
            and item["controller_lag_ms"] > window_ms
        ):
            item["classification"] = "CONTROLLER_UPDATE_DELAY"
            item["hypotheses"] = [
                "Update lag exceeds the configured simulation window; shared-clock assumption applies."
            ]
        else:
            item["classification"] = "CONSISTENT_OBSERVATIONS"
            item["hypotheses"] = [
                "Available views agree; unknown views are not treated as verified."
            ]
        item.pop("_ap_time", None)
    return {
        "model": "Simulated controller state and management-plane validation.",
        "clients": list(groups.values()),
        "limitations": [
            "Common-clock event model; not CAPWAP, a real wireless LAN controller, cloud-managed network or an RF diagnosis.",
            "Missing management events do not establish a device or transport failure.",
        ],
    }
