"""Candidate law selection: shared stateless law (default) or opt-in planners."""

from app.config import settings
from app.policies.configurable import configurable_policy
from app.policies.mpc_candidate import MpcCandidatePolicy
from app.policies.mpc_crowd import MpcCrowdPolicy
from app.policies.stateful_candidate import StatefulCandidatePolicy
from app.policies.waypoint_candidate import WaypointCandidatePolicy


def get_candidate_policy_fn():
    """Return the policy callable for CANDIDATE runs.

    Default ("shared") preserves every measured result in the docs. The
    verified MPC-lite law is opt-in via RW_CANDIDATE_LAW=mpc; the crowd-tuned
    variant uses mpc-crowd, and the experimental stateful/waypoint planners
    use stateful|waypoint. Each returns a fresh instance per call site;
    SimulationRunner.reset() isolates runs. Baseline runs never use this —
    they always use the shared law.
    """
    law = settings.RW_CANDIDATE_LAW.strip().lower()
    if law == "stateful":
        return StatefulCandidatePolicy()
    if law == "waypoint":
        return WaypointCandidatePolicy()
    if law == "mpc":
        return MpcCandidatePolicy()
    if law == "mpc-crowd":
        return MpcCrowdPolicy()
    return configurable_policy
