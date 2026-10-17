"""Verify running monitoring endpoints through their loopback APIs."""

import json
import os
import urllib.request


def fetch(base, path):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(base + path, timeout=5) as response:
        assert response.status == 200
        return json.load(response)


def main():
    prom = os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090")
    assert (
        fetch(prom, "/api/v1/query?query=up%7Bjob%3D%22eventpulse%22%7D")["data"][
            "result"
        ][0]["value"][1]
        == "1"
    )
    groups = fetch(prom, "/api/v1/rules")["data"]["groups"]
    assert groups and all(
        r.get("health") == "ok" and not r.get("lastError")
        for g in groups
        for r in g["rules"]
    )
    assert (
        fetch(os.getenv("GRAFANA_URL", "http://127.0.0.1:3000"), "/api/health")[
            "database"
        ]
        == "ok"
    )
    assert fetch(
        os.getenv("ALERTMANAGER_URL", "http://127.0.0.1:9093"), "/api/v2/status"
    )["versionInfo"]["version"]
    print("PASS: Prometheus target/rules, Grafana database and Alertmanager status")


if __name__ == "__main__":
    main()
