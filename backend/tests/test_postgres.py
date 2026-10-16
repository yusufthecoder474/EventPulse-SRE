"""Dedicated PostgreSQL integration test. Never point PG_TEST_URL at a shared database."""

import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import create_app


@pytest.mark.skipif(not os.getenv("PG_TEST_URL"), reason="PG_TEST_URL unavailable; PostgreSQL integration runs in CI")
def test_postgres_concurrent_capacity_and_rollback():
    app = create_app(os.environ["PG_TEST_URL"], fault_enabled=False)
    with app.state.engine.begin() as db:
        db.execute(text("TRUNCATE registrations, incidents"))
        db.execute(text("UPDATE events SET booked=0, capacity=3 WHERE id=1"))
    with TestClient(app) as client:

        def register(i):
            return client.post("/registrations", headers={"Idempotency-Key": f"postgres-{i}"}, json={"event_id": 1, "email": f"pg{i}@example.test"})

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(register, range(12)))
        assert sum(r.status_code == 201 for r in results) == 3
        assert sum(r.status_code == 409 for r in results) == 9
        event = client.get("/events").json()[0]
        assert event["booked"] == 3
        winner = next(i for i, r in enumerate(results) if r.status_code == 201)
        assert register(winner).status_code == 200
        assert client.get("/events").json()[0]["booked"] == 3
        # Actual connection invalidation must reconnect successfully through pre_ping.
        app.state.engine.dispose()
        assert client.get("/health/ready").status_code == 200
