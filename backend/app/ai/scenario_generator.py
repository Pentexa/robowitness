"""AI Scenario generation service."""

from typing import Optional
from app.ai.adapter import get_ai_adapter
from app.schemas.ai import AIProvenance
from app.schemas.scenario import ScenarioSpec


class ScenarioGeneratorService:
    def __init__(self):
        self.adapter = get_ai_adapter()

    def generate(self, user_prompt: Optional[str] = None) -> tuple[ScenarioSpec, AIProvenance]:
        prompt = user_prompt or "Generate a challenging dynamic obstacle scenario"
        spec, provenance = self.adapter.generate_scenario(prompt)
        return spec, provenance
