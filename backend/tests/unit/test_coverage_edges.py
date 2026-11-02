"""Remaining edge branches: JWT issuer, map warnings, adapter timeout."""

import time

import pytest
from app.config import settings
from app.maps.converter import convert_grid_to_scenario
from app.policies import local_adapter
from app.schemas.policy import PolicyConfig, SensorObservation


def _obs() -> SensorObservation:
    return SensorObservation(
        sample_tick=0,
        delivered_tick=0,
        age_s=0.0,
        valid=True,
        observed_pose={"yaw_rad": 0.0},
        goal_rel_x_m=5.0,
        goal_rel_y_m=0.0,
        goal_distance_m=5.0,
        obstacles=[],
    )


def test_local_policy_timeout_aborts(monkeypatch):
    slow = local_adapter.LOCAL_POLICY_DIR / "tmp_slow_policy.py"
    slow.write_text(
        "import time\n\n"
        "def policy(o, c):\n"
        "    time.sleep(30)\n"
        "    return {'linear_mps': 0.1, 'angular_radps': 0.0}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(local_adapter, "CALL_TIMEOUT_S", 0.5)
    try:
        with local_adapter.SubprocessPolicy("tmp_slow_policy") as plugin:
            with pytest.raises(local_adapter.LocalPolicyError, match="timed out"):
                plugin(_obs(), PolicyConfig())
    finally:
        slow.unlink(missing_ok=True)


def test_map_converter_many_clusters_warns_and_caps():
    # Checkerboard: many isolated single-cell clusters (>> 8).
    rows = []
    for r in range(16):
        row = "".join("#" if (c + r) % 2 == 0 else "." for c in range(24))
        rows.append(row)
    rows[15] = "S" + rows[15][1:]
    rows[14] = rows[14][:-2] + "G."
    grid = "\n".join(rows)
    spec, warnings = convert_grid_to_scenario("Dama", grid, 0.5)
    assert len(spec.obstacles) == 8
    assert any("kümesi" in w for w in warnings)


def test_map_converter_rejects_tiny_world():
    with pytest.raises(ValueError):
        convert_grid_to_scenario("Mini", "....\n.SG.\n....", 0.5)


def test_jwt_issuer_mismatch_rejected(client):
    import base64
    import hashlib
    import hmac
    import json as json_lib

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = b64(json_lib.dumps({"alg": "HS256"}).encode())
    body = b64(
        json_lib.dumps(
            {"sub": "x", "role": "admin", "iss": "https://evil.example", "exp": time.time() + 600}
        ).encode()
    )
    sig = hmac.new(b"s3cret", f"{header}.{body}".encode(), hashlib.sha256).digest()
    token = f"{header}.{body}.{b64(sig)}"

    prev_secret, prev_issuer = settings.RW_JWT_SECRET, settings.RW_OIDC_ISSUER
    settings.RW_JWT_SECRET = "s3cret"
    settings.RW_OIDC_ISSUER = "https://idp.example"
    try:
        res = client.get("/api/robots", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
    finally:
        settings.RW_JWT_SECRET, settings.RW_OIDC_ISSUER = prev_secret, prev_issuer
