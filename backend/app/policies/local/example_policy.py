"""Example local policy (user-written policy template).

Sözleşme: policy(observation, config) her adımda (60 Hz) çağrılır.
observation yalnızca gecikmeli sensör verisidir (gerçek konumlar YOK):
  - goal_rel_x_m, goal_rel_y_m : hedefe göreli konum (robot gövdesi)
  - obstacles: [{id, rel_x_m, rel_y_m, radius_m, distance_m}]
config: 5 sayısal ayar (max_speed_mps, safe_distance_m, ...).
Dönüş: {"linear_mps": float, "angular_radps": float}
"""

import math


def policy(observation, config):
    goal_x = observation["goal_rel_x_m"]
    goal_y = observation["goal_rel_y_m"]
    heading_to_goal = math.atan2(goal_y, goal_x)

    angular = max(-1.5, min(1.5, 2.0 * heading_to_goal))
    linear = config["max_speed_mps"] * max(0.0, math.cos(heading_to_goal))

    safe = config["safe_distance_m"] + config["reaction_margin_m"]
    for obstacle in observation["obstacles"]:
        dist = obstacle["distance_m"]
        if dist < safe:
            # Yakın engel: yavaşla ve engelin ters tarafına dön.
            linear *= max(0.0, dist / safe)
            if obstacle["rel_x_m"] > 0:
                angular += -1.0 if obstacle["rel_y_m"] > 0 else 1.0

    return {"linear_mps": linear, "angular_radps": angular}
