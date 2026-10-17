import math
import time
import threading
from collections import deque
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, Info, ProcessCollector, PlatformCollector

BUSINESS = ("/events", "/registrations", "/registrations/{registration_id}")
BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5)


def percentile(values, q):
    return sorted(values)[max(0, math.ceil(len(values) * q) - 1)] if values else None


def calculate(samples, window):
    n = len(samples)
    errors = sum(s["status"] >= 500 for s in samples)
    slow = sum(s["duration"] > 0.5 for s in samples)
    error_ratio = errors / n if n else None
    return {
        "requests": n,
        "errors": errors,
        "rps": n / window,
        "availability": 1 - error_ratio if n else None,
        "error_rate": error_ratio,
        "p50": percentile([s["duration"] for s in samples], 0.5),
        "p95": percentile([s["duration"] for s in samples], 0.95),
        "p99": percentile([s["duration"] for s in samples], 0.99),
        "latency_sli": 1 - slow / n if n else None,
        "budget_remaining": 1 - error_ratio / 0.01 if n else None,
        "burn_rate": error_ratio / 0.01 if n else None,
    }


class Telemetry:
    def __init__(self, window=60):
        self.window = window
        self.started = time.time()
        self.lock = threading.RLock()
        self.samples = deque(maxlen=100000)
        self.truncated = False
        self.registry = CollectorRegistry()
        ProcessCollector(registry=self.registry)
        PlatformCollector(registry=self.registry)
        self.requests = Counter("eventpulse_http_requests", "Completed HTTP requests", ["method", "route", "status"], registry=self.registry)
        # Zero series before the first failure make rate() observable at the first error scrape.
        for method, route in (("GET", "/events"), ("POST", "/registrations"), ("GET", "/registrations/{registration_id}")):
            for status in ("200", "201", "500", "503", "504"):
                self.requests.labels(method, route, status).inc(0)
        self.latency = Histogram("eventpulse_http_duration_seconds", "Request latency", ["method", "route"], buckets=BUCKETS, registry=self.registry)
        self.inflight = Gauge("eventpulse_inflight", "In-flight requests", registry=self.registry)
        self.ready = Gauge("eventpulse_database_ready", "Real database probe; simulated fault overrides to zero", registry=self.registry)
        self.uptime = Gauge("eventpulse_uptime_seconds", "Seconds since process start", registry=self.registry)
        self.registrations = Counter("eventpulse_registrations", "Registration attempts by outcome", ["outcome"], registry=self.registry)
        Info("eventpulse_service", "Build information", registry=self.registry).info({"version": "1.0.0"})

    def record(self, method, route, status, duration):
        method = method if method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS") else "OTHER"
        self.requests.labels(method, route, str(status)).inc()
        self.latency.labels(method, route).observe(duration)
        if route in BUSINESS:
            with self.lock:
                now = time.time()
                if len(self.samples) == self.samples.maxlen:
                    self.truncated = True
                self.samples.append({"at": now, "route": route, "status": status, "duration": duration})
                while self.samples and self.samples[0]["at"] < now - self.window:
                    self.samples.popleft()

    def summary(self, now=None):
        now = now or time.time()
        with self.lock:
            samples = [dict(s) for s in self.samples if s["at"] >= now - self.window]
        result = calculate(samples, self.window)
        history = []
        for i in range(20):
            start = now - self.window + i * self.window / 20
            subset = [s for s in samples if start <= s["at"] < start + self.window / 20]
            history.append({"at": start, **calculate(subset, self.window / 20)})
        endpoints = [{"route": route, **calculate([s for s in samples if s["route"] == route], self.window)} for route in BUSINESS]
        return {
            **result,
            "history": history,
            "endpoints": endpoints,
            "histogram": [{"le": b, "count": sum(s["duration"] <= b for s in samples)} for b in BUCKETS],
            "window_seconds": self.window,
            "window_start": now - self.window,
            "window_end": now,
            "sample_retention_truncated": self.truncated,
            "version": "1.0.0",
            "uptime": now - self.started,
            "source": "live process request observations",
            "availability_target": 0.99,
            "latency_target": 0.95,
        }
