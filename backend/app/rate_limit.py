"""In-memory sliding-window rate limiter (per actor, per minute).

Single-process protection against accidental floods; for multi-process
deployments put a real gateway in front. Disabled when the limit is 0.
"""

import threading
import time
from collections import defaultdict, deque

from app.config import settings

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def rate_limit_exceeded(actor: str) -> bool:
    limit = settings.RW_RATE_LIMIT_PER_MIN
    if limit <= 0:
        return False
    now = time.time()
    window_start = now - 60.0
    with _lock:
        hits = _hits[actor]
        while hits and hits[0] < window_start:
            hits.popleft()
        if len(hits) >= limit:
            return True
        hits.append(now)
        return False
