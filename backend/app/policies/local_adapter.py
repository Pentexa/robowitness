"""Subprocess adapter that lets a user policy drive the simulator safely-ish.

Isolation provided: separate process, per-call timeout, crash containment,
output validation + clamping to ControlCommand limits. Isolation NOT
provided: this is not a security sandbox — plugin code is plain Python with
the user's own privileges. Only run code you wrote and trust; never AI code.
"""

import json
import math
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

from app.schemas.policy import ControlCommand, PolicyConfig, SensorObservation

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_POLICY_DIR = BACKEND_DIR / "app" / "policies" / "local"

CALL_TIMEOUT_S = 5.0


class LocalPolicyError(RuntimeError):
    """Plugin load/call failure — the run fails honestly with this, never faked."""


def local_policy_path(name: str) -> Path:
    """Resolve a policy name to a file inside the local folder (no traversal).

    The path always comes from listing the folder (an allowlist); the
    caller's name only selects a key, never constructs a path.
    """
    if not name or any(c in name for c in ("/", "\\", ".", " ")):
        raise LocalPolicyError(f"Invalid local policy name: {name!r}")
    available = {p.stem: p for p in LOCAL_POLICY_DIR.glob("*.py") if p.is_file()}
    path = available.get(name)
    if path is None:
        raise LocalPolicyError(f"Local policy not found: {name}")
    return path.resolve()


class SubprocessPolicy:
    def __init__(self, name: str):
        self.name = name
        path = local_policy_path(name)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(BACKEND_DIR)
        self._proc = subprocess.Popen(
            [sys.executable, "-m", "app.policies.plugin_host", str(path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            cwd=str(BACKEND_DIR),
            env=env,
        )
        self._lines: queue.Queue = queue.Queue()
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()
        self._closed = False

    def _pump(self) -> None:
        try:
            for line in self._proc.stdout:  # type: ignore[union-attr]
                self._lines.put(line)
        except Exception:
            pass
        self._lines.put(None)

    def __call__(self, obs: SensorObservation, config: PolicyConfig) -> ControlCommand:
        if self._closed or self._proc.poll() is not None:
            raise LocalPolicyError(f"Local policy '{self.name}' process is not running")
        request = json.dumps({"observation": obs.model_dump(), "config": config.model_dump()})
        try:
            self._proc.stdin.write(request + "\n")  # type: ignore[union-attr]
            self._proc.stdin.flush()  # type: ignore[union-attr]
        except (BrokenPipeError, OSError) as exc:
            raise LocalPolicyError(f"Local policy '{self.name}' pipe broke: {exc}") from exc

        try:
            line = self._lines.get(timeout=CALL_TIMEOUT_S)
        except queue.Empty:
            self.close()
            raise LocalPolicyError(
                f"Local policy '{self.name}' timed out after {CALL_TIMEOUT_S}s — run aborted"
            )
        if line is None:
            self.close()
            raise LocalPolicyError(f"Local policy '{self.name}' process exited unexpectedly")
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LocalPolicyError(f"Local policy '{self.name}' returned non-JSON output") from exc
        if "error" in data:
            raise LocalPolicyError(f"Local policy '{self.name}': {data['error']}")

        linear = float(data["linear_mps"])
        angular = float(data["angular_radps"])
        if not (math.isfinite(linear) and math.isfinite(angular)):
            raise LocalPolicyError(f"Local policy '{self.name}' returned non-finite command")
        # Clamp to the simulator's command contract, never trust raw output.
        linear = max(-0.5, min(1.5, linear))
        angular = max(-math.pi, min(math.pi, angular))
        return ControlCommand(linear_mps=linear, angular_radps=angular)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
        except Exception:
            pass

    def __enter__(self) -> "SubprocessPolicy":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
