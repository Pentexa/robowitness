"""Baseline navigation policy — shares the single navigation law with configurable."""
import math
from app.policies.configurable import _core_navigation_law
from app.schemas.policy import ControlCommand, PolicyConfig, SensorObservation

def baseline_policy(obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
    """Deterministic navigation law based solely on delayed SensorObservation.

    Delegates to the single shared core law so baseline and candidate runs
    differ ONLY in the five allowed numeric PolicyConfig fields.
    """
    return _core_navigation_law(obs, config)
