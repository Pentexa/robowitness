"""AI Failure Investigator service."""

from app.ai.adapter import get_ai_adapter
from app.schemas.ai import AIProvenance, InvestigationResponse


class FailureInvestigatorService:
    def __init__(self):
        self.adapter = get_ai_adapter()

    def investigate(
        self, run_id: str, failure_summary: str
    ) -> tuple[InvestigationResponse, AIProvenance]:
        inv, provenance = self.adapter.investigate_failure(failure_summary)
        inv.run_id = run_id
        return inv, provenance
