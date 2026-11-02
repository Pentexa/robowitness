"""Image journeys with RECORDED SAM transport; real conversion/SQLite/PyBullet.

Default tests do not spend live credits. sam_still_response.json is a real
2026-11-03 SAM 3.1 response for the two red squares generated here, stripped
to status/output. Live coverage is scripts/sam_live_smoke.py.
"""

import base64
import io
import json
from pathlib import Path

import httpx
from PIL import Image, ImageDraw
import pytest

from app.ai.sam import SamAdapter, parse_sam_output, validate_image
from app.config import settings
from app.errors import RoboWitnessException
from app.evidence.integrity import verify_package_integrity
from app.evidence.recorder import RUN_REQUIRED_FILES
from app.jobs.repository import claim_next_job, update_job_status
from app.jobs.service import JobExecutionService

PREFIX = "/api/scenarios/from-image"
FIXTURE = Path(__file__).parent.parent / "fixtures" / "sam_still_response.json"


def photo_url(fmt="PNG", size=(1200, 800)):
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((460, 260, 520, 320), fill="red")
    draw.rectangle((700, 480, 760, 540), fill="red")
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    mime = {"PNG": "png", "JPEG": "jpeg", "WEBP": "webp", "GIF": "gif"}[fmt]
    return f"data:image/{mime};base64," + base64.b64encode(buffer.getvalue()).decode()


@pytest.fixture
def recorded_sam(client, monkeypatch):
    monkeypatch.setattr(settings, "RW_META_API_KEY", "test-key")
    monkeypatch.setattr(settings, "RW_META_BASE_URL", "https://api.meta.ai/v1")
    calls = []

    def transport(request):
        assert str(request.url) == "https://api.meta.ai/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "sam-3.1"
        assert payload["stream"] is False
        assert payload["metadata"]["include_confidence"] == "true"
        assert payload["input"][0]["content"][1]["type"] == "input_image"
        calls.append(payload["input"][0]["content"][0]["text"])
        return httpx.Response(200, json=json.loads(FIXTURE.read_text(encoding="utf-8")))

    monkeypatch.setattr(
        "app.api.routes_image_scenarios.SamAdapter",
        lambda: SamAdapter(httpx.Client(transport=httpx.MockTransport(transport))),
    )
    return calls


def detect(client):
    response = client.post(
        PREFIX + "/detect",
        json={
            "image_data_url": photo_url(),
            "concepts": ["red square"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def conversion(detection, **overrides):
    return {
        "detection_id": detection["detection_id"],
        "selected_ids": [d["id"] for d in detection["detections"]],
        "name": "Calibration squares",
        "width_m": 12,
        "height_m": 8,
        "overhead_confirmed": True,
        "start": {"x": 0.1, "y": 0.5},
        "goal": {"x": 0.9, "y": 0.5},
        **overrides,
    }


def test_image_detect_preview_save_reload_and_real_pybullet(client, recorded_sam):
    detection = detect(client)
    assert recorded_sam == ["red square"]
    assert detection["provenance"] == "LIVE_META"
    assert len(detection["detections"]) == 2
    assert len(detection["image_sha256"]) == 64
    before = client.get(PREFIX + "/saved").json()
    response = client.post(PREFIX + "/scenario", json=conversion(detection))
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["saved"] is False
    assert client.get(PREFIX + "/saved").json() == before
    spec = preview["scenario"]
    assert len(spec["obstacles"]) == 2
    assert all(o["motion"] == "static" and o["start"] == o["end"] for o in spec["obstacles"])
    # Original image y-down becomes world y-up. Enclosing circle is not undersized.
    for obs, item in zip(spec["obstacles"], detection["detections"]):
        box = item["box"]
        assert obs["start"]["y_m"] == pytest.approx(8 - (box["top"] + box["bottom"]) / 200)
        assert obs["radius_m"] >= (box["right"] - box["left"]) / 200
    saved = client.post(PREFIX + "/scenario", json=conversion(detection, save=True)).json()
    assert saved["saved"] is True
    assert saved["scenario"] == spec
    assert any(s["scenario"]["id"] == spec["id"] for s in client.get(PREFIX + "/saved").json())
    # Same ordinary run API/worker/oracle/evidence used by every other scenario.
    queued = client.post("/api/runs", json={"scenario": spec, "policy": {}})
    assert queued.status_code == 202, queued.text
    target = queued.json()
    for _ in range(100):
        job = claim_next_job("image-journey-test")
        assert job is not None
        if job.job_id == target["job_id"]:
            JobExecutionService().execute_simulation_run(job)
            update_job_status(job.job_id, status="completed", finished=True)
            break
        update_job_status(job.job_id, status="cancelled", finished=True)
    else:
        pytest.fail("image job was never claimed")
    result = client.get(f"/api/runs/{target['result_id']}").json()
    assert result["oracle_status"] == "PASS", result
    assert result["metrics"]["total_ticks"] > 0
    frames = client.get(f"/api/runs/{target['result_id']}/telemetry").json()
    assert frames["total"] == result["metrics"]["total_ticks"]
    assert frames["frames"][0]["obstacles"]
    directory = settings.artifacts_path / "runs" / target["result_id"]
    assert verify_package_integrity(directory, RUN_REQUIRED_FILES) == (True, [])


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_real_still_formats(fmt):
    assert validate_image(photo_url(fmt))[:2] == (1200, 800)


@pytest.mark.parametrize(
    "value",
    [
        "data:video/mp4;base64,AAAA",
        "https://example.com/x.jpg",
        "data:image/png;base64,@@@@",
        photo_url("GIF"),
        photo_url(size=(2100, 50)),
        "data:image/png;base64," + "A" * 7_000_001,
    ],
    ids=["video", "remote-url", "invalid-base64", "gif", "oversized-dimensions", "oversized-body"],
)
def test_invalid_image_rejected_before_provider(client, monkeypatch, value):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid images must never reach the paid provider")

    monkeypatch.setattr(SamAdapter, "detect", forbidden)
    assert (
        client.post(
            PREFIX + "/detect", json={"image_data_url": value, "concepts": ["chair"]}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"width_m": None},
        {"width_m": 21},
        {"height_m": 3},
        {"width_m": "nan"},
        {"overhead_confirmed": False},
        {"selected_ids": []},
        {"selected_ids": ["missing"]},
        {"selected_ids": ["red square:0", "red square:0"]},
        {"goal": {"x": 0.1, "y": 0.5}},
        {"goal": {"x": 0.409, "y": 0.364}},
        {"start": {"x": 0.409, "y": 0.364}},
        {"start": {"x": 0, "y": 0}},
    ],
)
def test_invalid_projection_never_saved(client, recorded_sam, overrides):
    detection = detect(client)
    response = client.post(PREFIX + "/scenario", json=conversion(detection, **overrides, save=True))
    assert response.status_code == 422, response.text


def test_workspace_isolation(client, recorded_sam):
    detection = detect(client)
    client.post(PREFIX + "/scenario", json=conversion(detection, save=True))
    other = {"X-Workspace-Id": "image-other-tenant"}
    assert client.get(PREFIX + "/saved", headers=other).json() == []
    assert (
        client.post(PREFIX + "/scenario", json=conversion(detection), headers=other).status_code
        == 404
    )
    bad = conversion(detection, detection_id="../../secrets")
    assert client.post(PREFIX + "/scenario", json=bad).status_code == 422


def test_oversized_object_not_silently_shrunk(client, recorded_sam, monkeypatch):
    detection = detect(client)
    from app.schemas.image_scenario import ImageBox
    from app.schemas.image_scenario import ImageDetectionResult
    from app.maps.image_converter import image_to_scenario
    from app.schemas.image_scenario import ImageScenarioRequest

    parsed = ImageDetectionResult.model_validate(detection)
    parsed.detections[0].box = ImageBox(left=400, top=100, right=1000, bottom=700)
    with pytest.raises(ValueError, match="will not be shrunk"):
        image_to_scenario(parsed, ImageScenarioRequest.model_validate(conversion(detection)))


@pytest.mark.parametrize(
    "text",
    [
        "I found two chairs",
        "<0f>",
        "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=10|>",
        "<1f>0<|box;bad|><|mask;bad|>",
    ],
)
def test_malformed_segmentation_never_becomes_objects(text):
    with pytest.raises(ValueError):
        parse_sam_output(text, "chair", 1200, 800)


def test_zero_matches_is_an_empty_completed_result():
    assert parse_sam_output("", "chair", 1200, 800) == []


@pytest.mark.parametrize(
    "status,body",
    [
        (401, {"secret": "do-not-expose"}),
        (429, {}),
        (500, {}),
        (200, {"status": "incomplete", "output": []}),
        (200, {"status": "completed", "output": []}),
    ],
)
def test_provider_failure_is_explicit_and_sanitized(monkeypatch, status, body):
    monkeypatch.setattr(settings, "RW_META_API_KEY", "secret-key")
    monkeypatch.setattr(settings, "RW_META_BASE_URL", "https://api.meta.ai/v1")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(status, json=body))
    )
    with pytest.raises(RoboWitnessException) as error:
        SamAdapter(client).detect(photo_url(), ["chair"], 1200, 800)
    assert error.value.status_code == 502
    assert "do-not-expose" not in str(error.value.detail)
    assert "secret-key" not in str(error.value.detail)


def test_missing_sam_key_never_falls_back_to_fake_detection(client):
    assert (
        client.post(
            PREFIX + "/detect", json={"image_data_url": photo_url(), "concepts": ["chair"]}
        ).status_code
        == 503
    )
