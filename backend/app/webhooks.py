"""Outbound webhooks: HMAC-signed event notifications (best-effort).

Configured via RW_WEBHOOK_URL / RW_WEBHOOK_SECRET. Delivery failures are
logged and swallowed — a dead webhook endpoint must never fail a job.
Signature: hex HMAC-SHA256 of the raw body in X-RoboWitness-Signature.
"""

import hashlib
import hmac
import json
import urllib.request
from datetime import datetime, timezone

from app.config import settings


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def notify(event: str, data: dict) -> bool:
    url = (settings.RW_WEBHOOK_URL or "").strip()
    if not url:
        return False
    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if settings.RW_WEBHOOK_SECRET:
        req.add_header("X-RoboWitness-Signature", _sign(body, settings.RW_WEBHOOK_SECRET))
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 (operator-configured URL)
            return 200 <= resp.status < 300
    except Exception as exc:
        print(f"[webhook] delivery failed for {event}: {exc}")
        return False
