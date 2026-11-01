"""One-shot live Meta smoke probe. Reads credentials ONLY from environment
(repo-root .env via app.config). Prints SANITIZED fields only: HTTP status,
latency, token counts, model id echoed by the server. NEVER prints the key,
request bodies, or raw provider output. Exit 0 on authenticated success."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.adapter import MetaAdapter
from app.config import settings


def main() -> int:
    if not settings.RW_META_API_KEY or not settings.RW_META_BASE_URL:
        print("SKIP: no live credentials configured (RW_META_API_KEY/BASE_URL empty)")
        return 3
    adapter = MetaAdapter(
        api_key=settings.RW_META_API_KEY,
        base_url=settings.RW_META_BASE_URL,
        model=settings.RW_META_MODEL,
    )
    probe = adapter.smoke()
    safe = {k: v for k, v in probe.items()}
    print("smoke:", safe, flush=True)
    if not probe.get("ok"):
        print("RESULT: provider unreachable/unauthorized -> LIVE_META stays UNVERIFIED", flush=True)
        return 2
    spec, prov = adapter.generate_scenario("Generate a valid warehouse scenario")
    if spec is None:
        print("RESULT: smoke ok but generation invalid -> LIVE_META UNVERIFIED", flush=True)
        return 2
    print(
        "RESULT: LIVE_META ok model=%s id=%s usage=%s"
        % (settings.RW_META_MODEL, spec.id, adapter.last_usage),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
