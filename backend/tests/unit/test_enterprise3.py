"""Enterprise round 3: DB API keys, idempotency, rate limit, webhooks, schedules, ops."""

import hashlib
import hmac
import json

import pytest
from app.config import settings
from app.jobs.repository import claim_next_job
from app.jobs.schedules import enqueue_due_schedules
from app.jobs.service import JobExecutionService

REF_POLICY = {"id": "baseline-v1"}


@pytest.fixture
def rate_limit_on():
    previous = settings.RW_RATE_LIMIT_PER_MIN
    settings.RW_RATE_LIMIT_PER_MIN = 3
    yield
    settings.RW_RATE_LIMIT_PER_MIN = previous
    from app.rate_limit import _hits

    _hits.clear()


def test_db_api_key_lifecycle_enforces_auth(client):
    created = client.post(
        "/api/admin/api-keys",
        json={"label": "ci", "role": "admin", "workspace_id": "ws-key-test"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    plaintext = body["api_key"]
    assert plaintext.startswith("rw_")
    # Creating the first key enforces auth immediately, so the keeper key is
    # created WITH the first key's credentials.
    keeper = client.post(
        "/api/admin/api-keys",
        json={"label": "keeper", "role": "admin", "workspace_id": "default"},
        headers={"X-API-Key": plaintext},
    ).json()
    try:
        # Stored only as a hash: listing never leaks the plaintext.
        listed = client.get("/api/admin/api-keys", headers={"X-API-Key": plaintext}).json()
        assert plaintext not in json.dumps(listed)

        headers = {"X-API-Key": plaintext}
        assert client.get("/api/robots", headers=headers).status_code == 200

        revoked = client.delete(
            f"/api/admin/api-keys/{body['key_id']}",
            headers={"X-API-Key": keeper["api_key"]},
        )
        assert revoked.status_code == 200
        # With another active key present, auth stays enforced: revoked + no key fail.
        assert client.get("/api/robots", headers=headers).status_code == 401
        assert client.get("/api/robots").status_code == 401
        assert (
            client.get("/api/robots", headers={"X-API-Key": keeper["api_key"]}).status_code == 200
        )
    finally:
        # Revoke the keeper so the shared test session returns to open local mode.
        client.delete(
            f"/api/admin/api-keys/{keeper['key_id']}",
            headers={"X-API-Key": keeper["api_key"]},
        )


def test_first_key_must_be_admin(client):
    # No active keys exist in this session (key lifecycle test revoked all of
    # its keys), so a non-admin first key is refused to prevent lockout.
    res = client.post(
        "/api/admin/api-keys",
        json={"label": "kilit", "role": "viewer", "workspace_id": "default"},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "FIRST_KEY_MUST_BE_ADMIN"


def test_idempotency_key_prevents_duplicate_runs(client):
    scenario = client.get("/api/scenarios/reference").json()[0]
    headers = {"Idempotency-Key": "test-idem-1"}
    first = client.post(
        "/api/runs", json={"scenario": scenario, "policy": REF_POLICY}, headers=headers
    )
    second = client.post(
        "/api/runs", json={"scenario": scenario, "policy": REF_POLICY}, headers=headers
    )
    assert first.status_code == second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]

    other = client.post(
        "/api/runs",
        json={"scenario": scenario, "policy": REF_POLICY},
        headers={"Idempotency-Key": "test-idem-2"},
    )
    assert other.json()["job_id"] != first.json()["job_id"]


def test_security_headers_and_request_id_present(client):
    res = client.get("/api/robots")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["X-Request-Id"].startswith("req-")


def test_rate_limit_returns_429(client, rate_limit_on):
    codes = [client.get("/api/robots").status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert 429 in codes[3:]


def test_webhook_signed_battery_notification(client, monkeypatch):
    from app import webhooks

    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=5):
        captured["url"] = req.full_url
        captured["body"] = req.data
        captured["signature"] = req.headers.get("X-robowitness-signature")
        return FakeResponse()

    monkeypatch.setattr(webhooks.urllib.request, "urlopen", fake_urlopen)
    previous_url, previous_secret = settings.RW_WEBHOOK_URL, settings.RW_WEBHOOK_SECRET
    settings.RW_WEBHOOK_URL = "https://hooks.example/rw"
    settings.RW_WEBHOOK_SECRET = "whsec-test"
    try:
        res = client.post(
            "/api/batteries",
            json={
                "robot_id": "robot-turtlebot3-waffle-pi",
                "scenario_ids": ["RW-LIB-009"],
                "policy": REF_POLICY,
            },
        )
        assert res.status_code == 202
        service = JobExecutionService()
        while True:
            job = claim_next_job("test-webhook")
            assert job is not None
            if job.kind == "battery_run":
                service.execute_battery_run(job)
                break
            service.execute_simulation_run(job)
    finally:
        settings.RW_WEBHOOK_URL, settings.RW_WEBHOOK_SECRET = previous_url, previous_secret

    assert captured["url"] == "https://hooks.example/rw"
    payload = json.loads(captured["body"])
    assert payload["event"] == "battery.completed"
    expected = hmac.new(b"whsec-test", captured["body"], hashlib.sha256).hexdigest()
    assert captured["signature"] == expected


def test_schedule_create_and_due_enqueue(client):
    created = client.post(
        "/api/batteries/schedules",
        json={
            "name": "Saatlik sınav",
            "robot_id": "robot-jackal",
            "policy": REF_POLICY,
            "scenario_ids": ["RW-LIB-009"],
            "interval_minutes": 60,
        },
    )
    assert created.status_code == 201, created.text
    schedule_id = created.json()["schedule_id"]
    try:
        # Force it due, then let the schedule engine enqueue exactly one battery.
        from app.db import get_db

        with get_db() as conn:
            conn.execute(
                "UPDATE battery_schedules SET next_run_at = '2000-01-01T00:00:00+00:00' "
                "WHERE schedule_id = ?",
                (schedule_id,),
            )
            conn.commit()
        assert enqueue_due_schedules(force=True) == 1
        service = JobExecutionService()
        job = None
        while True:
            claimed = claim_next_job("test-schedule")
            assert claimed is not None
            if claimed.kind == "battery_run":
                job = claimed
                break
            service.execute_simulation_run(claimed)
        service.execute_battery_run(job)
        card = client.get(f"/api/batteries/{job.result_id}")
        assert card.status_code == 200
        assert card.json()["summary"]["total"] == 1
    finally:
        client.delete(f"/api/batteries/schedules/{schedule_id}")


def test_prometheus_and_backup_and_retention_dry_run(client):
    prom = client.get("/api/prom")
    assert prom.status_code == 200
    assert "robowitness_jobs" in prom.text

    backup = client.post("/api/admin/backup")
    assert backup.status_code == 201, backup.text
    assert len(backup.json()["sha256"]) == 64
    assert client.get("/api/admin/backups").json()["backups"]

    retention = client.post("/api/admin/retention", json={"older_than_days": 3650, "dry_run": True})
    assert retention.status_code == 200
    assert retention.json()["dry_run"] is True
    assert "counts" in retention.json()

    # Restore round-trip: restoring the just-made backup (same content) is safe.
    restored = client.post("/api/admin/restore", json={"file": backup.json()["file"]})
    assert restored.status_code == 200, restored.text
    assert restored.json()["sha256"] == backup.json()["sha256"]
    assert restored.json()["safety_backup"].startswith("pre-restore-")
    assert client.get("/api/robots").status_code == 200
    missing = client.post("/api/admin/restore", json={"file": "../robowitness.sqlite3"})
    assert missing.status_code == 404
