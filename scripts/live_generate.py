"""Attempt one real validated generation via the adapter (sanitized output only)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.adapter import MetaAdapter
from app.config import settings

a = MetaAdapter(api_key=settings.RW_META_API_KEY, base_url=settings.RW_META_BASE_URL,
                model=settings.RW_META_MODEL)
spec, prov = a.generate_scenario("Generate a valid warehouse simulation scenario")
print("provenance:", prov, flush=True)
print("usage:", a.last_usage, flush=True)
if spec is not None:
    print("scenario id:", spec.id, "kind:", spec.kind, "seed:", spec.seed,
          "obstacles:", len(spec.obstacles), flush=True)
else:
    print("RESULT: generation invalid -> LIVE_META UNVERIFIED", flush=True)
