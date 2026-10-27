"""Prompt templates for scenario generation and failure investigation."""

SCENARIO_GEN_PROMPT = """You are an expert robotics verification engineer.
Generate a valid warehouse simulation scenario in JSON conforming exactly to the ScenarioSpec schema.
Do NOT output explanations or markdown. Output raw JSON only.
World width: 12.0m, height: 8.0m.
"""

FAILURE_INVESTIGATION_PROMPT = """Analyze the following simulation failure telemetry and events.
Provide a concise, testable engineering hypothesis explaining why the collision or violation occurred.
Propose a partial patch for the controller parameters (max_speed_mps, safe_distance_m, reaction_margin_m, brake_gain, obstacle_prediction_horizon_s).
Output raw JSON matching the InvestigationResponse schema.
"""
