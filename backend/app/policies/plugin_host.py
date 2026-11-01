"""Plugin host process: loads ONE user policy file and answers per-tick queries.

Protocol (stdin/stdout, one JSON object per line):
  request : {"observation": {...}, "config": {...}}
  response: {"linear_mps": float, "angular_radps": float}  or  {"error": "..."}

The user module must define:  def policy(observation: dict, config: dict) -> dict | tuple
This file runs in a dedicated subprocess so a crashing/hanging plugin cannot
take the worker down with it. It is NOT a security sandbox: the plugin is
plain Python and must only ever be code the user wrote and trusts.
AI-generated code must never be placed in the local policy folder.
"""

import importlib.util
import json
import sys
import traceback


def _load_policy(path: str):
    spec = importlib.util.spec_from_file_location("rw_user_policy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load policy module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn = getattr(module, "policy", None)
    if not callable(fn):
        raise RuntimeError("Policy module must define a callable: policy(observation, config)")
    return fn


def _normalize(result) -> dict:
    if isinstance(result, dict):
        return {
            "linear_mps": float(result["linear_mps"]),
            "angular_radps": float(result["angular_radps"]),
        }
    if isinstance(result, (list, tuple)) and len(result) == 2:
        return {"linear_mps": float(result[0]), "angular_radps": float(result[1])}
    lin = getattr(result, "linear_mps", None)
    ang = getattr(result, "angular_radps", None)
    if lin is not None and ang is not None:
        return {"linear_mps": float(lin), "angular_radps": float(ang)}
    raise RuntimeError("policy() must return {'linear_mps', 'angular_radps'} or a 2-tuple")


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: plugin_host <policy_file>"}), flush=True)
        return 2
    try:
        policy_fn = _load_policy(sys.argv[1])
    except Exception:
        print(json.dumps({"error": "LOAD_FAILED: " + traceback.format_exc(limit=3)}), flush=True)
        return 2

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            result = policy_fn(req["observation"], req["config"])
            print(json.dumps(_normalize(result)), flush=True)
        except Exception:
            print(
                json.dumps({"error": "POLICY_ERROR: " + traceback.format_exc(limit=3)}),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
