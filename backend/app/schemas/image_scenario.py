"""Still-image segmentation and explicit, user-calibrated planar projection."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.scenario import ScenarioSpec


class ImageBox(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    left: int = Field(ge=0)
    top: int = Field(ge=0)
    right: int = Field(gt=0)
    bottom: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("Bounding box must have positive area")
        return self


class ImageDetection(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str
    concept: str
    box: ImageBox
    confidence: float | None = Field(default=None, ge=0, le=1)


class ImageDetectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_data_url: str = Field(max_length=7_000_000)
    concepts: list[str] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def phrases(self):
        self.concepts = list(dict.fromkeys(c.strip() for c in self.concepts))
        if any(not c or len(c) > 80 or any(x in c for x in "\n\r,;<>") for c in self.concepts):
            raise ValueError("Use up to three short object concepts, one per line")
        return self


class ImageDetectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detection_id: str
    image_width: int = Field(gt=0, le=2048)
    image_height: int = Field(gt=0, le=2048)
    image_sha256: str
    model: Literal["sam-3.1"] = "sam-3.1"
    provenance: Literal["LIVE_META"] = "LIVE_META"
    detections: list[ImageDetection] = Field(max_length=100)


class ImagePoint(BaseModel):
    """Normalized image coordinates, origin at top left."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class ImageScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    detection_id: str = Field(pattern=r"^img-[a-f0-9]{24}$")
    selected_ids: list[str] = Field(min_length=1, max_length=8)
    name: str = Field(default="Image scenario", min_length=1, max_length=120)
    width_m: float = Field(ge=6, le=20)
    height_m: float = Field(ge=4, le=15)
    overhead_confirmed: Literal[True]
    start: ImagePoint
    goal: ImagePoint
    save: bool = False

    @model_validator(mode="after")
    def unique_selection(self):
        if len(set(self.selected_ids)) != len(self.selected_ids):
            raise ValueError("Each detected object can be selected only once")
        return self


class ImageScenarioResult(BaseModel):
    scenario: ScenarioSpec
    name: str
    detection_id: str
    provenance: Literal["LIVE_META"] = "LIVE_META"
    model: Literal["sam-3.1"] = "sam-3.1"
    saved: bool = False
    warnings: list[str] = Field(default_factory=list)
