import hashlib
import json
import time
from typing import Any

from config import IDEMPOTENCY_TTL_SECONDS

# In-memory idempotency store.
# Key: (device_id, idempotency_key) → {"status": int, "body": dict, "body_hash": str, "ts": float}
_STORE: dict[tuple[str, str], dict[str, Any]] = {}


def _canonical_hash(body: bytes) -> str:
    """SHA-256 of the raw request body bytes (canonicalized by the client)."""
    return hashlib.sha256(body).hexdigest()


def _evict_expired() -> None:
    """Remove entries older than the TTL. Called lazily on every lookup."""
    now = time.time()
    expired = [k for k, v in _STORE.items() if now - v["ts"] > IDEMPOTENCY_TTL_SECONDS]
    for k in expired:
        del _STORE[k]


def check_idempotency(
    idempotency_key: str,
    device_id: str,
    body_bytes: bytes,
) -> tuple[bool, bool, dict[str, Any] | None]:
    """Check the idempotency store for a previously-seen key.

    Returns:
        (is_replay, is_mismatch, cached_response)
        - is_replay=True, is_mismatch=False → return cached_response as-is
        - is_replay=True, is_mismatch=True  → caller should return 422
        - is_replay=False                   → new request; caller should store after handling
    """
    _evict_expired()
    store_key = (device_id, idempotency_key)
    entry = _STORE.get(store_key)
    if entry is None:
        return False, False, None

    incoming_hash = _canonical_hash(body_bytes)
    if entry["body_hash"] != incoming_hash:
        return True, True, None

    return True, False, entry


def store_idempotency(
    idempotency_key: str,
    device_id: str,
    body_bytes: bytes,
    status_code: int,
    response_body: dict[str, Any],
) -> None:
    """Persist the outcome of a successful mutating request."""
    _STORE[(device_id, idempotency_key)] = {
        "status": status_code,
        "body": response_body,
        "body_hash": _canonical_hash(body_bytes),
        "ts": time.time(),
    }


def get_device_id(request_headers: Any) -> str:
    """Extract a stable device identifier from the request.

    The simulator derives this from the Authorization token value (which the
    Flutter app ties to its device session). Falls back to a constant for
    unauthenticated calls so the logic stays uniform.
    """
    auth = request_headers.get("Authorization", "anonymous")
    token = auth.removeprefix("Bearer ").strip()
    return token or "anonymous"
