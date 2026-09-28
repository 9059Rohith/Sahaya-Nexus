import hashlib
import hmac
import ipaddress
import re
import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from ..config import settings

_lock = threading.Lock()
_attempts: dict[str, deque[float]] = defaultdict(deque)
_last_cleanup = 0.0
_redis_client = None

# A single atomic operation gives all API workers the same one-minute bucket.
_INCREMENT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], 60) end
return count
"""


class RateLimitUnavailable(Exception):
    """The configured shared limiter cannot currently accept writes."""


class InvalidProxyIdentity(Exception):
    """A mutation did not come through the configured signed web proxy."""


def shared_limiter_status() -> str:
    if not settings.redis_url:
        return "in_process"
    try:
        global _redis_client
        if _redis_client is None:
            from redis import Redis

            _redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
        return "redis_shared" if _redis_client.ping() else "unavailable"
    except Exception:
        return "unavailable"


def signed_client_address(request: Request) -> str | None:
    secret = settings.bff_shared_secret
    if not secret:
        return None
    address = request.headers.get("x-sahaya-client-address")
    stamp = request.headers.get("x-sahaya-client-time")
    signature = request.headers.get("x-sahaya-client-signature")
    if not address or not stamp or not signature:
        return None
    try:
        ipaddress.ip_address(address)
        if abs(time.time() - int(stamp)) > 30:
            return None
    except ValueError:
        return None
    expected = hmac.new(secret.encode(), f"{stamp}:{address}".encode(), hashlib.sha256).hexdigest()
    return address if hmac.compare_digest(expected, signature) else None

LIMITS = {
    "/api/v1/auth/login": 60,
    "/api/v1/auth/register": 30,
    "/api/v1/requests/interpret": 60,
    "/api/v1/speech/transcribe": 20,
    "/api/v1/reports/abuse": 20,
}


def permitted(request: Request) -> bool:
    global _last_cleanup
    if request.method not in {"POST", "PATCH", "PUT", "DELETE"}:
        return True
    path = request.url.path
    limit = LIMITS.get(path)
    if limit is None:
        limit = 30 if path.endswith("/evidence") else 180
    signed_address = signed_client_address(request)
    if settings.bff_shared_secret and not signed_address:
        raise InvalidProxyIdentity
    identity = f"client:{signed_address}" if signed_address else (request.headers.get("authorization") or (request.client.host if request.client else "unknown"))
    route_bucket = re.sub(r"/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}", "/:id", path)
    key = hashlib.sha256(f"{identity}:{route_bucket}".encode()).hexdigest()
    if settings.redis_url:
        global _redis_client
        try:
            if _redis_client is None:
                from redis import Redis

                _redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
            return int(_redis_client.eval(_INCREMENT, 1, f"sahaya:limit:{key}")) <= limit
        except Exception as exc:
            raise RateLimitUnavailable from exc
    instant = time.monotonic()
    with _lock:
        if instant - _last_cleanup > 120:
            for stale_key in [candidate for candidate, entries in _attempts.items() if not entries or entries[-1] < instant - 60]:
                del _attempts[stale_key]
            _last_cleanup = instant
        entries = _attempts[key]
        while entries and entries[0] < instant - 60:
            entries.popleft()
        if len(entries) >= limit:
            return False
        entries.append(instant)
    return True
