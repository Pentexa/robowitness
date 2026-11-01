"""Named policy profiles: the 5 numeric parameters saved under a user name."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.policy import PolicyConfig


class PolicyProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    policy: PolicyConfig


class PolicyProfile(PolicyProfileCreate):
    profile_id: str
    source: Literal["builtin", "user"]
    created_at: str
    updated_at: str
