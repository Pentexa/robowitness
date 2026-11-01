"""Enterprise round 2: JWT/OIDC, workspace backup, trend, fleet batteries."""

import base64
import hashlib
import hmac
import json
import time

import pytest
from app.config import settings
from app.jobs.repository import claim_next_job
from app.jobs.service import JobExecutionService

POLICY = {"id": "baseline-v1"}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _hs256_token(secret: str, payload: dict) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps(payload).encode())
    sig = hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64(sig)}"


@pytest.fixture
def jwt_secret():
    previous = settings.RW_JWT_SECRET
    settings.RW_JWT_SECRET = "test-secret"
    yield
    settings.RW_JWT_SECRET = previous


def test_hs256_jwt_auth_and_role_enforcement(client, jwt_secret):
    token = _hs256_token(
        "test-secret",
        {"sub": "ayse", "role": "viewer", "workspace": "default", "exp": time.time() + 600},
    )
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/robots", headers=headers).status_code == 200
    denied = client.post(
        "/api/robots",
        headers=headers,
        json={
            "brand": "JwtBot",
            "model": "J-1",
            "drive_type": "differential_drive",
            "body_radius_m": 0.25,
            "sensor_type": "LiDAR",
            "sensor_range_m": 4.0,
            "sensor_latency_ms": 0,
            "sensor_noise_std_m": 0.0,
        },
    )
    assert denied.status_code == 403  # viewer cannot write, even with valid JWT


def test_hs256_tampered_and_expired_rejected(client, jwt_secret):
    good = _hs256_token("test-secret", {"sub": "x", "role": "admin", "exp": time.time() + 600})
    tampered = good[:-2] + "AA"
    assert (
        client.get("/api/robots", headers={"Authorization": f"Bearer {tampered}"}).status_code
        == 401
    )
    expired = _hs256_token("test-secret", {"sub": "x", "role": "admin", "exp": time.time() - 10})
    assert (
        client.get("/api/robots", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    )
    wrong_secret = _hs256_token(
        "baska-secret", {"sub": "x", "role": "admin", "exp": time.time() + 600}
    )
    assert (
        client.get("/api/robots", headers={"Authorization": f"Bearer {wrong_secret}"}).status_code
        == 401
    )


def test_rs256_oidc_with_generated_key(client, monkeypatch):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    import app.jwt_auth as jwt_auth

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = key.public_key().public_numbers()

    def to_b64url_int(value: int) -> str:
        raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
        return _b64(raw)

    jwk = {
        "kty": "RSA",
        "kid": "test-key-1",
        "n": to_b64url_int(numbers.n),
        "e": to_b64url_int(numbers.e),
    }
    monkeypatch.setattr(jwt_auth, "fetch_jwks", lambda url: [jwk])
    previous = settings.RW_OIDC_JWKS_URL
    settings.RW_OIDC_JWKS_URL = "https://idp.example/jwks.json"
    settings.RW_OIDC_ISSUER = ""
    try:
        header = _b64(json.dumps({"alg": "RS256", "kid": "test-key-1"}).encode())
        body = _b64(
            json.dumps({"sub": "oidc-user", "role": "editor", "exp": time.time() + 600}).encode()
        )
        signing = f"{header}.{body}".encode()
        signature = key.sign(signing, padding.PKCS1v15(), hashes.SHA256())
        token = f"{header}.{body}.{_b64(signature)}"
        res = client.get("/api/robots", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, res.text
    finally:
        settings.RW_OIDC_JWKS_URL = previous


def test_workspace_export_import_roundtrip(client):
    headers_a = {"X-Workspace-Id": "ws-export-a"}
    headers_b = {"X-Workspace-Id": "ws-export-b"}
    created = client.post(
        "/api/robots",
        headers=headers_a,
        json={
            "brand": "ExportBot",
            "model": "E-1",
            "drive_type": "differential_drive",
            "body_radius_m": 0.25,
            "sensor_type": "LiDAR",
            "sensor_range_m": 4.0,
            "sensor_latency_ms": 0,
            "sensor_noise_std_m": 0.0,
        },
    )
    assert created.status_code == 201
    try:
        bundle = client.get("/api/workspaces/export", headers=headers_a)
        assert bundle.status_code == 200
        assert len(bundle.json()["robots"]) == 1

        restored = client.post("/api/workspaces/import", headers=headers_b, json=bundle.json())
        assert restored.status_code == 200, restored.text
        assert restored.json()["inserted"]["robots"] == 1

        in_b = client.get("/api/robots", headers=headers_b).json()
        assert any(r["brand"] == "ExportBot" for r in in_b)
    finally:
        rid = created.json()["robot_id"]
        client.delete(f"/api/robots/{rid}", headers=headers_a)
        for r in client.get("/api/robots", headers=headers_b).json():
            if r["brand"] == "ExportBot":
                client.delete(f"/api/robots/{r['robot_id']}", headers=headers_b)


def test_battery_trend_and_fleet(client):
    fleet = client.post(
        "/api/batteries/fleet",
        json={
            "robot_ids": ["robot-turtlebot3-waffle-pi", "robot-spot", "robot-yok"],
            "scenario_ids": ["RW-LIB-009"],
            "policy": POLICY,
        },
    )
    assert fleet.status_code == 202, fleet.text
    body = fleet.json()
    assert len(body["jobs"]) == 1
    skipped_reasons = {s["robot_id"]: s["reason"] for s in body["skipped"]}
    assert "ROBOT_NOT_FOUND" in skipped_reasons["robot-yok"]
    assert "ROBOT_NOT_SIM_COMPATIBLE" in skipped_reasons["robot-spot"]

    while True:
        job = claim_next_job("test-fleet")
        if job is None:
            break
        JobExecutionService().execute_battery_run(job)

    trend = client.get("/api/batteries/trend?robot_id=robot-turtlebot3-waffle-pi")
    assert trend.status_code == 200
    points = trend.json()
    assert len(points) >= 1
    last = points[-1]
    assert last["passed"] == 1 and last["total"] == 1 and last["pass_rate"] == 1.0
