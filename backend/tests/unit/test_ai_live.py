"""Live-transport tests with mocked HTTP — no real credentials, no network."""

import json
import httpx
from app.ai.adapter import MetaAdapter


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _scenario_json():
    return {
        "schema_version": "1.0",
        "id": "RW-MOCK-001",
        "kind": "dynamic_obstacle",
        "seed": 99,
        "world": {
            "type": "warehouse",
            "width_m": 12.0,
            "height_m": 8.0,
            "duration_limit_s": 30.0,
            "fixed_timestep_s": 1.0 / 60.0,
        },
        "robot": {
            "kind": "differential_drive",
            "start": {"x_m": 1.0, "y_m": 4.0, "yaw_rad": 0.0},
            "goal": {"x_m": 11.0, "y_m": 4.0},
            "goal_radius_m": 0.35,
            "body_radius_m": 0.25,
            "sensor_latency_ms": 450,
            "sensor_noise_std_m": 0.0,
        },
        "obstacles": [
            {
                "id": "O1",
                "shape": "circle",
                "radius_m": 0.35,
                "motion": "ping_pong",
                "start": {"x_m": 6.0, "y_m": 1.0},
                "end": {"x_m": 6.0, "y_m": 7.0},
                "speed_mps": 0.45,
            }
        ],
        "oracle": {
            "collision_free": True,
            "min_clearance_m": 0.25,
            "must_reach_goal": True,
            "max_duration_s": 30.0,
            "max_stuck_duration_s": 3.0,
        },
    }


def test_smoke_ok_reports_no_secrets():
    def handler(request):
        assert request.headers["Authorization"].startswith("Bearer ")
        return httpx.Response(200, json={"data": [{"id": "m1"}]})

    a = MetaAdapter("sk-test-SECRET-abc123", "https://x.test/v1", "m", client=_client(handler))
    out = a.smoke()
    assert out["ok"] is True and out["models_count"] == 1
    assert "SECRET" not in json.dumps(out)


def test_smoke_401_is_unavailable_without_leak():
    def handler(request):
        return httpx.Response(401, json={"error": "bad key detail should not leak"})

    a = MetaAdapter("sk-test-SECRET-abc123", "https://x.test/v1", "m", client=_client(handler))
    out = a.smoke()
    assert out["ok"] is False
    assert "SECRET" not in json.dumps(out) and "bad key" not in json.dumps(out)


def test_valid_scenario_parses_live():
    def handler(request):
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(_scenario_json())}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    a = MetaAdapter(
        "sk-test-SECRET-abc123", "https://x.test/v1", "m", client=_client(handler), max_retries=0
    )
    spec, prov = a.generate_scenario("make one")
    assert prov == "LIVE_META" and spec.id == "RW-MOCK-001"
    assert a.last_usage.get("prompt_tokens") == 10


def test_invalid_json_yields_unavailable_not_crash():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    a = MetaAdapter(
        "sk-test-SECRET-abc123", "https://x.test/v1", "m", client=_client(handler), max_retries=0
    )
    spec, prov = a.generate_scenario("make one")
    assert spec is None and prov == "UNAVAILABLE"


def test_missing_key_never_touches_network():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={})

    a = MetaAdapter("", "https://x.test/v1", "m", client=_client(handler))
    assert a.smoke()["ok"] is False
    assert a.generate_scenario("x") == (None, "UNAVAILABLE")
    assert calls == []


def test_malicious_patch_keys_rejected():
    bad = {
        "investigation_id": "i",
        "run_id": "r",
        "failure_tick": 1,
        "hypothesis": "h",
        "evidence_summary": "e",
        "suggested_patch": {"max_speed_mps": 0.5, "exec": "rm -rf"},
        "provenance": "LIVE_META",
    }

    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(bad)}}]})

    a = MetaAdapter(
        "sk-test-SECRET-abc123", "https://x.test/v1", "m", client=_client(handler), max_retries=0
    )
    inv, prov = a.investigate_failure("summary")
    assert inv is None and prov == "UNAVAILABLE"


def test_controlled_regenerate_repairs_invalid_output():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            bad_payload = {"bad": "json"}
            import json as _J

            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": _J.dumps(bad_payload)}}]},
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(_scenario_json())}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    a = MetaAdapter(
        "sk-test-SECRET-abc123", "https://x.test/v1", "m", client=_client(handler), max_retries=0
    )
    spec, prov = a.generate_scenario("make one")
    assert prov == "LIVE_META" and spec is not None and spec.id == "RW-MOCK-001"
    assert len(calls) == 2
