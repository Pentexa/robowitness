"""Paid live SAM 3.1 -> scaled scenario -> ordinary worker -> real PyBullet.

Run against the local backend+worker. Default input is an explicitly rendered
overhead calibration image, NOT a real scene or physical-world safety proof.
An optional --image / --concept pair tests your own rectified floor photo.
"""

import argparse
import base64
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import time

import httpx
from PIL import Image, ImageDraw, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--concept", default="red square")
    parser.add_argument("--width-m", type=float, default=12)
    parser.add_argument("--height-m", type=float, default=8)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    output = root / "artifacts" / "sam_smoke" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    output.mkdir(parents=True)
    if args.image:
        with Image.open(args.image) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1600, 1600))
    else:
        image = Image.new("RGB", (1200, 800), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((460, 260, 520, 320), fill="red")
        draw.rectangle((700, 480, 760, 540), fill="red")
    image.save(output / "input.png")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    headers = {"X-API-Key": os.environ["RW_API_KEY"]} if os.environ.get("RW_API_KEY") else {}
    with httpx.Client(base_url=args.api, timeout=200, headers=headers) as client:

        def post(path, payload):
            response = client.post(path, json=payload)
            if response.status_code >= 400:
                raise RuntimeError(f"{path}: HTTP {response.status_code}: {response.text}")
            return response.json()

        detection = post(
            "/api/scenarios/from-image/detect",
            {
                "image_data_url": data_url,
                "concepts": [args.concept],
            },
        )
        assert detection["provenance"] == "LIVE_META"
        assert detection["model"] == "sam-3.1"
        assert detection["detections"], "SAM completed but found no matching objects"
        if not args.image:
            assert len(detection["detections"]) == 2, detection
        (output / "detections.json").write_text(json.dumps(detection, indent=2), encoding="utf-8")
        scenario = post(
            "/api/scenarios/from-image/scenario",
            {
                "detection_id": detection["detection_id"],
                "selected_ids": [d["id"] for d in detection["detections"]],
                "name": "SAM live calibration",
                "width_m": args.width_m,
                "height_m": args.height_m,
                "overhead_confirmed": True,
                "start": {"x": 0.1, "y": 0.5},
                "goal": {"x": 0.9, "y": 0.5},
                "save": True,
            },
        )
        (output / "scenario.json").write_text(json.dumps(scenario, indent=2), encoding="utf-8")
        saved = client.get("/api/scenarios/from-image/saved").json()
        assert any(s["scenario"]["id"] == scenario["scenario"]["id"] for s in saved)
        job = post("/api/runs", {"scenario": scenario["scenario"], "policy": {}})
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            state = client.get(f"/api/jobs/{job['job_id']}").json()
            if state["status"] == "completed":
                break
            assert state["status"] not in ("failed", "cancelled"), state
            time.sleep(0.5)
        else:
            raise RuntimeError("Worker did not complete the image scenario within 120 seconds")
        result = client.get(f"/api/runs/{job['result_id']}").json()
        frames = client.get(f"/api/runs/{job['result_id']}/telemetry").json()
        assert result["metrics"]["total_ticks"] > 0 and frames["frames"]
        if not args.image:
            assert result["oracle_status"] == "PASS", result
        report = {
            "source": "user_photo" if args.image else "rendered_overhead_calibration",
            "detections": len(detection["detections"]),
            "run_id": job["result_id"],
            "scenario_id": scenario["scenario"]["id"],
            "result": result,
        }
        (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"artifacts": str(output), **report}, indent=2))


if __name__ == "__main__":
    main()
