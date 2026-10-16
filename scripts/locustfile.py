from locust import HttpUser, between, task
import uuid


class Attendee(HttpUser):
    wait_time = between(0.2, 1)

    @task(5)
    def browse(self):
        self.client.get("/events")

    @task(1)
    def register(self):
        key = uuid.uuid4().hex
        self.client.post(
            "/registrations",
            json={"event_id": 1, "email": f"{key}@example.test"},
            headers={"Idempotency-Key": key},
        )
