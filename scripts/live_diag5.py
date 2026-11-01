"""Diagnose live scenario validation failures: error LOCATIONS only, no values."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.adapter import MetaAdapter
from app.config import settings
from app.schemas.scenario import ScenarioSpec
from pydantic import ValidationError
import json as J

a = MetaAdapter(api_key=settings.RW_META_API_KEY, base_url=settings.RW_META_BASE_URL,
                model=settings.RW_META_MODEL, max_retries=0)

# Replicate one raw call to inspect structure (no content printed).
import httpx
payload = {
    "model": settings.RW_META_MODEL,
    "messages": [
        {"role": "system", "content": "You output ONLY a JSON object. Mirror this exact structure: " + MetaAdapter._SCENARIO_TEMPLATE},
        {"role": "user", "content": "Generate a valid warehouse simulation scenario."},
    ],
    "temperature": 0,
    "max_tokens": 4000,
}
r = httpx.post(settings.RW_META_BASE_URL.rstrip("/") + "/chat/completions",
               headers={"Authorization": "Bearer " + settings.RW_META_API_KEY,
                        "Content-Type": "application/json"},
               json=payload, timeout=90)
body = r.json()
c = str(body["choices"][0]["message"]["content"])
print("http:", r.status_code, "len:", len(c), flush=True)
s, e = c.find("{"), c.rfind("}")
if s < 0:
    print("no object", flush=True)
    raise SystemExit
try:
    d = J.loads(c[s:e + 1])
except Exception as ex:
    print("parse fail:", type(ex).__name__, flush=True)
    raise SystemExit
print("top keys:", sorted(d.keys()) if isinstance(d, dict) else type(d), flush=True)
try:
    ScenarioSpec.model_validate(d)
    print("VALIDATES", flush=True)
except ValidationError as ve:
    print("err locs:", [(str(x.get("loc", "")), x.get("type", "")) for x in ve.errors()][:12], flush=True)
