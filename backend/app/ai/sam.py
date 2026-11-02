"""Real SAM 3.1 Responses API adapter; no offline/fabricated detections.

Contract: https://dev.meta.ai/docs/sam/segmenting
Wire decoding: Meta's official dependency-free meta-sam-parser.
"""

import base64
import hashlib
import io
import re
import warnings

import httpx
from meta_sam_parser import CompletedOutcome, image_segmentation_format
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.errors import RoboWitnessException
from app.schemas.image_scenario import ImageBox, ImageDetection


def validate_image(data_url: str) -> tuple[int, int, str]:
    """Decode and verify actual still-image bytes before any paid request."""
    try:
        header, encoded = data_url.split(",", 1)
        formats = {
            "data:image/png;base64": "PNG",
            "data:image/jpeg;base64": "JPEG",
            "data:image/webp;base64": "WEBP",
        }
        if header not in formats:
            raise ValueError("Only PNG, JPEG and WebP still images are supported")
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > 5_000_000:
            raise ValueError("Image must be between 1 byte and 5 MB")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as img:
                width, height = img.size
                if img.format != formats[header]:
                    raise ValueError("The file must be a single still image of the declared type")
                if not (16 <= width <= 2048 and 16 <= height <= 2048):
                    raise ValueError("Image dimensions must be 16–2048 pixels per side")
                img.verify()
            # Metadata access can load PNG pixels, so inspect it on a fresh
            # handle AFTER verify(), which requires the original unopened stream.
            with Image.open(io.BytesIO(raw)) as img:
                if getattr(img, "n_frames", 1) != 1:
                    raise ValueError("Animated images are not supported")
                if img.getexif().get(274, 1) != 1:
                    raise ValueError("Normalize image orientation before uploading")
        return width, height, hashlib.sha256(raw).hexdigest()
    except (
        ValueError,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise RoboWitnessException(
            status_code=422,
            code="INVALID_STILL_IMAGE",
            message="Upload a valid PNG, JPEG or WebP still (16–2048 px, ≤5 MB)",
        ) from exc


def parse_sam_output(text: str, concept: str, width: int, height: int) -> list[ImageDetection]:
    """Validate boxes AND masks; use conservative boxes for circle projection."""
    if len(text) > 4_000_000:
        raise ValueError("SAM output exceeds the image segmentation limit")
    # Bound source dimensions and mask allocations before the strict decoder.
    for size in re.finditer(r"data=(\d+),(\d+),", text):
        h, w = map(int, size.groups())
        if h > height or w > width or h * w > width * height:
            raise ValueError("SAM mask dimensions exceed the source image")
    parser = image_segmentation_format().create_parser()
    parser.push(text)
    result = parser.finish(CompletedOutcome()).result
    if any(d.severity == "error" for d in result.diagnostics):
        raise ValueError("SAM returned malformed segmentation records")
    if any(r.kind == "text" for r in result.records):
        raise ValueError("SAM returned text instead of segmentation")
    found = []
    for record in result.records:
        if record.kind != "box":
            continue
        if not (
            0 <= record.left < record.right <= width and 0 <= record.top < record.bottom <= height
        ):
            raise ValueError("SAM box is outside the image")
        found.append(
            ImageDetection(
                id=f"{concept}:{record.object_id}",
                concept=concept,
                box=ImageBox(
                    left=record.left, top=record.top, right=record.right, bottom=record.bottom
                ),
                confidence=record.confidence,
            )
        )
    if len(found) > 100:
        raise ValueError("Too many detections; use a more specific object concept")
    return found


class SamAdapter:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client

    def detect(self, data_url: str, concepts: list[str], width: int, height: int):
        if not settings.RW_META_API_KEY or not settings.RW_META_BASE_URL:
            raise RoboWitnessException(
                status_code=503,
                code="SAM_NOT_CONFIGURED",
                message="Meta API key and base URL are required for SAM 3.1",
            )
        found = []
        try:
            with self.client or httpx.Client(
                timeout=httpx.Timeout(60, connect=10), follow_redirects=False
            ) as client:
                for concept in concepts:
                    response = client.post(
                        settings.RW_META_BASE_URL.rstrip("/") + "/responses",
                        headers={"Authorization": f"Bearer {settings.RW_META_API_KEY}"},
                        json={
                            "model": "sam-3.1",
                            "stream": False,
                            "metadata": {"include_confidence": "true"},
                            "input": [
                                {
                                    "type": "message",
                                    "role": "user",
                                    "content": [
                                        {"type": "input_text", "text": concept},
                                        {"type": "input_image", "image_url": data_url},
                                    ],
                                }
                            ],
                        },
                    )
                    response.raise_for_status()
                    body = response.json()
                    if body.get("status") != "completed":
                        raise ValueError("Segmentation did not complete")
                    texts = [
                        part["text"]
                        for item in body.get("output", [])
                        for part in item.get("content", [])
                        if part.get("type") == "output_text"
                    ]
                    if len(texts) != 1:
                        raise ValueError("Expected one SAM output text lane")
                    found.extend(parse_sam_output(texts[0], concept, width, height))
            if len(found) > 100:
                raise ValueError("Too many detections")
            return found
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            # Never include provider response bodies, uploaded bytes or credentials.
            raise RoboWitnessException(
                status_code=502,
                code="SAM_PROVIDER_ERROR",
                message=(
                    "SAM 3.1 could not complete valid segmentation; retry or use a clearer image"
                ),
            ) from exc
