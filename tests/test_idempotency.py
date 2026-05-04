"""Unit tests for idempotency store — Spec §8."""
import time

import pytest

# We need to import from the backend_simulator package root.
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from middleware.idempotency import (
    _STORE,
    check_idempotency,
    store_idempotency,
)


@pytest.fixture(autouse=True)
def clear_store():
    """Reset the in-memory store before each test."""
    _STORE.clear()
    yield
    _STORE.clear()


def test_first_request_is_not_a_replay():
    is_replay, is_mismatch, cached = check_idempotency("key-1", "dev-1", b'{"amount":1000}')
    assert is_replay is False
    assert is_mismatch is False
    assert cached is None


def test_duplicate_key_same_body_returns_cached():
    body = b'{"amount":1000}'
    store_idempotency("key-2", "dev-1", body, 201, {"id": "txn_abc"})

    is_replay, is_mismatch, cached = check_idempotency("key-2", "dev-1", body)
    assert is_replay is True
    assert is_mismatch is False
    assert cached is not None
    assert cached["body"] == {"id": "txn_abc"}
    assert cached["status"] == 201


def test_duplicate_key_different_body_returns_mismatch():
    body1 = b'{"amount":1000}'
    body2 = b'{"amount":9999}'
    store_idempotency("key-3", "dev-1", body1, 201, {"id": "txn_def"})

    is_replay, is_mismatch, cached = check_idempotency("key-3", "dev-1", body2)
    assert is_replay is True
    assert is_mismatch is True
    assert cached is None


def test_different_device_same_key_is_independent():
    body = b'{"amount":500}'
    store_idempotency("key-4", "dev-A", body, 201, {"id": "txn_for_A"})

    # dev-B has NOT stored this key — should be a fresh request.
    is_replay, is_mismatch, cached = check_idempotency("key-4", "dev-B", body)
    assert is_replay is False


def test_expired_entry_is_evicted(monkeypatch):
    """Entries older than TTL should be treated as new requests."""
    body = b'{"amount":100}'
    store_idempotency("key-5", "dev-1", body, 201, {"id": "txn_old"})

    # Backdate the stored timestamp so it appears expired.
    _STORE[("dev-1", "key-5")]["ts"] = time.time() - 90_001  # past 24h TTL

    is_replay, is_mismatch, cached = check_idempotency("key-5", "dev-1", body)
    assert is_replay is False
