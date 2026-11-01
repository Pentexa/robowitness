"""List the user policy files available in app/policies/local/."""

import ast
from pathlib import Path

from app.config import settings
from app.policies.local_adapter import LOCAL_POLICY_DIR


def list_local_policies() -> dict:
    policies = []
    if LOCAL_POLICY_DIR.exists():
        for path in sorted(LOCAL_POLICY_DIR.glob("*.py")):
            if path.name.startswith("__"):
                continue
            description = ""
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
                doc = ast.get_docstring(tree)
                if doc:
                    description = doc.strip().splitlines()[0]
            except Exception:
                description = ""
            policies.append({"name": path.stem, "file": path.name, "description": description})
    return {"enabled": settings.local_policy_enabled, "policies": policies}


def local_policy_dir() -> Path:
    return LOCAL_POLICY_DIR
