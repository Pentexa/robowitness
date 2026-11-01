"""AI adapter protocols and model implementations.

Live transport assumes an OpenAI-compatible chat-completions endpoint
(`{base_url}/chat/completions`, Bearer auth). No Meta endpoint or model ID is
invented: values come only from explicit environment configuration, and any
transport/schema failure yields UNAVAILABLE with a sanitized reason — never a
fabricated scenario, hypothesis, or verified verdict.
"""

import json
import time
from typing import Any, Dict, Optional, Protocol
import httpx
from app.config import settings
from app.schemas.ai import AIProvenance, InvestigationResponse
from app.schemas.policy import PolicyPatch
from app.schemas.scenario import ScenarioSpec


class ModelAdapter(Protocol):
    def generate_scenario(self, prompt: str) -> tuple[Optional[ScenarioSpec], AIProvenance]: ...

    def investigate_failure(
        self, failure_summary: str
    ) -> tuple[Optional[InvestigationResponse], AIProvenance]: ...


class OfflineReferenceAdapter:
    def __init__(self, reference_spec_path=None):
        self.reference_spec_path = reference_spec_path

    def generate_scenario(self, prompt: str) -> tuple[Optional[ScenarioSpec], AIProvenance]:
        from app.schemas.scenario import (
            ObstacleSpec,
            OracleSpec,
            Point2D,
            Pose2D,
            RobotSpec,
            ScenarioSpec,
            WorldSpec,
        )

        spec = ScenarioSpec(
            id="RW-AI-GEN-001",
            kind="dynamic_obstacle",
            seed=4242,
            world=WorldSpec(width_m=12.0, height_m=8.0, duration_limit_s=30.0),
            robot=RobotSpec(
                start=Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0),
                goal=Point2D(x_m=11.0, y_m=4.0),
                goal_radius_m=0.35,
                body_radius_m=0.25,
                sensor_latency_ms=450,
                sensor_noise_std_m=0.01,
            ),
            obstacles=[
                ObstacleSpec(
                    id="AI_O1",
                    shape="circle",
                    radius_m=0.35,
                    motion="ping_pong",
                    start=Point2D(x_m=6.0, y_m=1.2),
                    end=Point2D(x_m=6.0, y_m=6.8),
                    speed_mps=0.45,
                )
            ],
            oracle=OracleSpec(max_duration_s=30.0),
        )
        return spec, "OFFLINE_REFERENCE"

    def investigate_failure(
        self, failure_summary: str
    ) -> tuple[Optional[InvestigationResponse], AIProvenance]:
        inv = InvestigationResponse(
            investigation_id="inv-offline-ref",
            run_id="run-ref",
            failure_tick=124,
            hypothesis=(
                "Delayed observations report the obstacle late, so braking starts too late."
            ),
            evidence_summary=(
                "At tick 124, clearance fell below 0.0 m while speed stayed 0.75 m/s."
            ),
            suggested_patch=PolicyPatch(
                max_speed_mps=0.45,
                safe_distance_m=0.85,
                reaction_margin_m=0.15,
                brake_gain=3.0,
                obstacle_prediction_horizon_s=0.60,
            ),
            provenance="OFFLINE_REFERENCE",
        )
        return inv, "OFFLINE_REFERENCE"


class MetaAdapter:
    """Bounded OpenAI-compatible transport. Secrets never leave the request
    headers; failures are sanitized (no key, no raw body) and surfaced as
    UNAVAILABLE."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_s: Optional[int] = None,
        max_retries: Optional[int] = None,
        client: Optional[httpx.Client] = None,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.timeout_s = timeout_s if timeout_s is not None else settings.RW_AI_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.RW_AI_MAX_RETRIES
        self._client = client
        self.last_usage: Dict[str, Any] = {}

    def _client_or_default(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=self.timeout_s)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"}

    def smoke(self) -> Dict[str, Any]:
        """Cheap authenticated probe: GET {base}/models. Sanitized result only."""
        if not self.api_key or not self.base_url:
            return {"ok": False, "reason": "missing_credentials_or_base_url"}
        started = time.time()
        try:
            client = self._client_or_default()
            resp = client.get(self.base_url + "/models", headers=self._headers())
            latency_ms = round((time.time() - started) * 1000, 1)
            if resp.status_code == 200:
                try:
                    count = len(resp.json().get("data", []))
                except Exception:
                    count = -1
                return {
                    "ok": True,
                    "http_status": 200,
                    "latency_ms": latency_ms,
                    "models_count": count,
                }
            return {
                "ok": False,
                "reason": "http_error",
                "http_status": resp.status_code,
                "latency_ms": latency_ms,
            }
        except Exception as e:
            return {
                "ok": False,
                "reason": type(e).__name__,
                "latency_ms": round((time.time() - started) * 1000, 1),
            }

    def _chat_json(self, system_prompt: str, user_content: str) -> Optional[Dict[str, Any]]:
        """One bounded JSON chat call with a single controlled regenerate."""
        if not self.api_key or not self.base_url or not self.model:
            return None
        user_content = user_content[: settings.RW_AI_MAX_INPUT_CHARS]
        # Output budget floor: reasoning models spend tokens thinking before
        # emitting JSON; 1000 truncates them mid-reasoning. Still bounded.
        output_budget = max(settings.RW_AI_MAX_OUTPUT_TOKENS, 4000)
        # NOTE: this endpoint ignores response_format=json_object (it then
        # emits "{}"); a plain prompt with an explicit template works instead.
        # Validation stays strict Pydantic — no lowering of any gate.
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0,
            "max_tokens": output_budget,
        }
        attempts = 1 + self.max_retries
        for attempt in range(attempts):
            try:
                client = self._client_or_default()
                resp = client.post(
                    self.base_url + "/chat/completions", headers=self._headers(), json=payload
                )
                if resp.status_code in (429,) or resp.status_code >= 500:
                    time.sleep(min(2.0**attempt, 8.0))
                    continue
                if resp.status_code != 200:
                    return None
                try:
                    body = resp.json()
                    self.last_usage = body.get("usage", {}) or {}
                    text = body["choices"][0]["message"]["content"]
                    return json.loads(text)
                except (KeyError, IndexError, ValueError, TypeError, AttributeError):
                    continue
            except (httpx.TimeoutException, httpx.TransportError):
                time.sleep(min(2.0**attempt, 8.0))
                continue
            except Exception:
                return None
        return None

    _SCENARIO_TEMPLATE = (
        '{"schema_version": "1.0", "id": "RW-AI-001", "kind": "dynamic_obstacle", '
        '"seed": 4242, "world": {"type": "warehouse", "width_m": 12.0, "height_m": 8.0, '
        '"duration_limit_s": 30.0, "fixed_timestep_s": 0.016666666666666666}, '
        '"robot": {"kind": "differential_drive", '
        '"start": {"x_m": 1.0, "y_m": 4.0, "yaw_rad": 0.0}, '
        '"goal": {"x_m": 11.0, "y_m": 4.0}, '
        '"goal_radius_m": 0.35, "body_radius_m": 0.25, '
        '"sensor_latency_ms": 450, "sensor_noise_std_m": 0.0}, '
        '"obstacles": [{"id": "O1", "shape": "circle", "radius_m": 0.35, '
        '"motion": "ping_pong", "start": {"x_m": 6.0, "y_m": 1.0}, '
        '"end": {"x_m": 6.0, "y_m": 7.0}, "speed_mps": 0.45}], '
        '"oracle": {"collision_free": true, "min_clearance_m": 0.25, '
        '"must_reach_goal": true, "max_duration_s": 30.0, "max_stuck_duration_s": 3.0}}'
    )

    def _extract_fix_hint(self, error) -> str:
        """Field paths only (never values) for one controlled regenerate."""
        try:
            locs = sorted({str(e.get("loc", "")) for e in error.errors()})
            hint = "Previous output failed validation at fields: "
            return hint + ", ".join(locs[:8]) + ". Output corrected JSON only."
        except Exception:
            return "Previous output was invalid JSON. Output corrected JSON only."

    def generate_scenario(self, prompt: str) -> tuple[Optional[ScenarioSpec], AIProvenance]:
        from pydantic import ValidationError as _VE

        sys_prompt = (
            "You output ONLY a JSON object matching the RoboWitness ScenarioSpec schema "
            "(schema_version 1.0, warehouse 12x8m, differential_drive robot, circle obstacles). "
            "No code, no markdown, no extra keys. "
            "Mirror this exact structure with valid values: " + self._SCENARIO_TEMPLATE
        )
        data = self._chat_json(sys_prompt, prompt)
        if data is None:
            return None, "UNAVAILABLE"
        try:
            return ScenarioSpec.model_validate(data), "LIVE_META"
        except _VE as ve:
            data2 = self._chat_json(sys_prompt, prompt + " " + self._extract_fix_hint(ve))
            if data2 is None:
                return None, "UNAVAILABLE"
            try:
                return ScenarioSpec.model_validate(data2), "LIVE_META"
            except Exception:
                return None, "UNAVAILABLE"
        except Exception:
            return None, "UNAVAILABLE"

    _INVESTIGATION_TEMPLATE = (
        '{"investigation_id": "inv-ai-001", "run_id": "run-ref", '
        '"failure_tick": 358, '
        '"hypothesis": "Delayed observations report the obstacle late, '
        'so braking starts too late.", '
        '"evidence_summary": "Measured over 359 recorded ticks with first contact at tick 358.", '
        '"suggested_patch": {"max_speed_mps": 0.45, "safe_distance_m": 0.85, '
        '"reaction_margin_m": 0.15, "brake_gain": 3.0, '
        '"obstacle_prediction_horizon_s": 0.6}, '
        '"provenance": "LIVE_META"}'
    )

    def investigate_failure(
        self, failure_summary: str
    ) -> tuple[Optional[InvestigationResponse], AIProvenance]:
        from pydantic import ValidationError as _VE

        sys_prompt = (
            "You output ONLY a JSON object with keys: investigation_id (string), run_id (string), "
            "failure_tick (int), hypothesis (string), evidence_summary (string), "
            "suggested_patch (object with ONLY numeric keys among max_speed_mps, safe_distance_m, "
            "reaction_margin_m, brake_gain, obstacle_prediction_horizon_s), provenance (string). "
            "No code, no markdown, no extra keys. "
            "Mirror this exact structure with valid values: " + self._INVESTIGATION_TEMPLATE
        )
        data = self._chat_json(sys_prompt, failure_summary)
        if data is None:
            return None, "UNAVAILABLE"
        try:
            inv = InvestigationResponse.model_validate(data)
            inv.provenance = "LIVE_META"
            return inv, "LIVE_META"
        except _VE as ve:
            data2 = self._chat_json(sys_prompt, failure_summary + " " + self._extract_fix_hint(ve))
            if data2 is None:
                return None, "UNAVAILABLE"
            try:
                inv2 = InvestigationResponse.model_validate(data2)
                inv2.provenance = "LIVE_META"
                return inv2, "LIVE_META"
            except Exception:
                return None, "UNAVAILABLE"
        except Exception:
            return None, "UNAVAILABLE"


def get_ai_adapter() -> ModelAdapter:
    if settings.RW_AI_MODE == "live" and settings.RW_META_API_KEY:
        return MetaAdapter(
            api_key=settings.RW_META_API_KEY,
            base_url=settings.RW_META_BASE_URL,
            model=settings.RW_META_MODEL,
        )
    return OfflineReferenceAdapter()
