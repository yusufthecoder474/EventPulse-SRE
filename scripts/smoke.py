"""Real API integration assertions. Uses synthetic, idempotent smoke identity."""

import os
import json
import urllib.error
import urllib.request


def request(path, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    req = urllib.request.Request(
        os.environ.get("API_URL", "http://127.0.0.1:8000") + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
    )
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
        req, timeout=5
    ) as response:
        return response.status, dict(response.headers), response.read()


def main():
    status, _, data = request("/events")
    assert status == 200 and len(json.loads(data)) > 0
    body = {"event_id": 1, "email": "smoke-v2@example.test"}
    first, headers, raw = request(
        "/registrations", body, "eventpulse-v2-smoke-idempotent"
    )
    assert first in (200, 201) and headers.get(
        "x-request-id", headers.get("X-Request-ID")
    )
    if os.getenv("SMOKE_EXPECT_EXISTING") == "true":
        assert first == 200, "Registration did not survive recreation"
    registration = json.loads(raw)
    assert request("/registrations", body, "eventpulse-v2-smoke-idempotent")[0] == 200
    assert (
        json.loads(request("/registrations/" + registration["id"])[2]) == registration
    )
    metrics = request("/metrics")[2].decode()
    for metric in [
        "eventpulse_http_requests_total",
        "eventpulse_http_duration_seconds_bucket",
        "eventpulse_database_ready",
        "eventpulse_service_info",
    ]:
        assert metric in metrics
    # Only business-safe metadata is printed; do not output attendee records.
    print(
        "PASS: events, registration, idempotency, retrieval, correlation and instrumentation"
    )


if __name__ == "__main__":
    main()
