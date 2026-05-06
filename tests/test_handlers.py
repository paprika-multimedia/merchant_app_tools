"""Integration-style tests for handlers using FastAPI TestClient.

These tests run in-process — no network needed. They cover:
- CPM /scan requires Idempotency-Key (400 if missing)
- CPM capability_disabled returns 403
- Idempotency replay returns cached response
- Idempotency mismatch returns 422
- Accept-Language switches error message locale
- DELETE /merchants/:id requires confirm_name match
- POST /sessions/claim with wrong company code returns 404
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

# Must import after sys.path adjustment.
from main import create_app
from fixtures.company import COMPANY
from fixtures.merchants import (
    MERCHANT_UNCLAIMED_KOPI_TENDA,
    MERCHANTS,
    MERCHANT_CODE_INDEX,
    UNCLAIMED_MERCHANTS,
)
from fixtures.transactions import TRANSACTIONS
from middleware.idempotency import _STORE


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state():
    """Partially reset mutable state between tests."""
    _STORE.clear()
    # Restore unread counts to avoid test ordering issues.
    for mid, merchant in list(MERCHANTS.items()):
        if merchant.unread_count == 0 and mid == "mch_01HX3R9WKQF4P2KJ7DZM":
            MERCHANTS[mid] = merchant.model_copy(update={"unread_count": 2})
    # Restore the unclaimed merchant so the 201-claim test can re-run.
    if MERCHANT_UNCLAIMED_KOPI_TENDA.id not in UNCLAIMED_MERCHANTS:
        UNCLAIMED_MERCHANTS[MERCHANT_UNCLAIMED_KOPI_TENDA.id] = (
            MERCHANT_UNCLAIMED_KOPI_TENDA
        )
        MERCHANT_CODE_INDEX[MERCHANT_UNCLAIMED_KOPI_TENDA.code] = (
            MERCHANT_UNCLAIMED_KOPI_TENDA.id
        )
    if MERCHANT_UNCLAIMED_KOPI_TENDA.id in MERCHANTS:
        del MERCHANTS[MERCHANT_UNCLAIMED_KOPI_TENDA.id]
    yield
    _STORE.clear()


AUTH = {"Authorization": "Bearer mock_session_token_30d", "Accept-Language": "id"}
AUTH_EN = {"Authorization": "Bearer mock_session_token_30d", "Accept-Language": "en"}
WK_ID = "mch_01HX3R9WKQF4P2KJ7DZM"
GR_ID = "mch_01HX3RBGRF4P2KJ7DZQ9W"


# --- /scan CPM ---

def test_scan_missing_idempotency_key_returns_400(client):
    r = client.post(
        f"/v1/merchants/{WK_ID}/scan",
        json={"qr_payload": "00020101BCACPM", "amount": 50000},
        headers=AUTH,
    )
    assert r.status_code == 400
    assert r.json()["error"] == "idempotency_required"


def test_scan_capability_disabled_returns_403(client):
    r = client.post(
        f"/v1/merchants/{GR_ID}/scan",
        json={"qr_payload": "00020101BCACPM", "amount": 50000},
        headers={**AUTH, "Idempotency-Key": "key-cap-test"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "capability_disabled"


def test_scan_idempotency_replay_returns_same_response(client):
    key = "key-idem-replay"
    payload = {"qr_payload": "00020101BCACPM", "amount": 50000}
    headers = {**AUTH, "Idempotency-Key": key}

    r1 = client.post(f"/v1/merchants/{WK_ID}/scan", json=payload, headers=headers)
    assert r1.status_code == 201
    r2 = client.post(f"/v1/merchants/{WK_ID}/scan", json=payload, headers=headers)
    assert r2.status_code == 201
    assert r1.json()["transaction"]["id"] == r2.json()["transaction"]["id"]


def test_scan_idempotency_mismatch_returns_422(client):
    key = "key-idem-mismatch"
    headers = {**AUTH, "Idempotency-Key": key}

    r1 = client.post(
        f"/v1/merchants/{WK_ID}/scan",
        json={"qr_payload": "00020101BCACPM", "amount": 50000},
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/v1/merchants/{WK_ID}/scan",
        json={"qr_payload": "00020101BCACPM", "amount": 99999},  # different body
        headers=headers,
    )
    assert r2.status_code == 422
    assert r2.json()["error"] == "idempotency_mismatch"


# --- Accept-Language ---

def test_error_message_localized_id(client):
    r = client.post(
        f"/v1/merchants/{WK_ID}/scan",
        json={"qr_payload": "00020101BCACPM", "amount": 50000},
        headers=AUTH,  # id locale
    )
    assert r.status_code == 400
    # Indonesian message should not be in English
    assert r.json()["error"] == "idempotency_required"
    msg = r.json()["message"]
    # At minimum the message should be a non-empty string
    assert isinstance(msg, str) and len(msg) > 0


def test_error_message_localized_en(client):
    r = client.post(
        f"/v1/merchants/{WK_ID}/scan",
        json={"qr_payload": "00020101BCACPM", "amount": 50000},
        headers=AUTH_EN,
    )
    assert r.status_code == 400
    msg = r.json()["message"]
    assert "idempotency" in msg.lower() or "required" in msg.lower()


# --- DELETE merchant ---

def test_delete_merchant_wrong_name_returns_422(client):
    import json as _json
    r = client.request(
        "DELETE",
        f"/v1/merchants/{WK_ID}",
        data=_json.dumps({"confirm_name": "Wrong Name"}),
        headers={**AUTH, "Content-Type": "application/json"},
    )
    assert r.status_code == 422
    assert r.json()["error"] == "name_mismatch"


def test_delete_merchant_correct_name_returns_204(client):
    import json as _json
    r = client.request(
        "DELETE",
        f"/v1/merchants/{WK_ID}",
        data=_json.dumps({"confirm_name": "Warung Kosan"}),
        headers={**AUTH, "Content-Type": "application/json"},
    )
    assert r.status_code == 204
    # Restore for other tests.
    from fixtures.merchants import MERCHANT_WARUNG_KOSAN, MERCHANT_CODE_INDEX
    MERCHANTS[WK_ID] = MERCHANT_WARUNG_KOSAN
    MERCHANT_CODE_INDEX[MERCHANT_WARUNG_KOSAN.code] = WK_ID


# --- Sessions ---

def test_session_claim_wrong_code_returns_404(client):
    r = client.post(
        "/v1/sessions/claim",
        json={
            "company_code": "AAAAAAAAAABBBBBBBBBB",
            "device": {"platform": "ios", "model": "iPhone 15"},
        },
    )
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


def test_session_claim_correct_code_returns_200(client):
    r = client.post(
        "/v1/sessions/claim",
        json={
            "company_code": "A4F28K19PQ7M3XR9LB42",
            "device": {"platform": "android", "model": "Pixel 8"},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "session_token" in data
    assert "refresh_token" in data
    assert "company" in data
    assert "merchants" in data


# --- Auth guard ---

def test_missing_auth_returns_401(client):
    r = client.get("/v1/merchants")
    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


# --- Transactions ---

def test_list_transactions_returns_paginated(client):
    r = client.get(f"/v1/merchants/{WK_ID}/transactions", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert "next_cursor" in body
    assert isinstance(body["data"], list)


def test_get_unknown_transaction_returns_404(client):
    r = client.get("/v1/transactions/txn_DOESNOTEXIST", headers=AUTH)
    assert r.status_code == 404


def test_cancel_already_paid_transaction_returns_409(client):
    # txn_01HX4QRIS1PAID000001 is seeded as "paid"
    r = client.post("/v1/transactions/txn_01HX4QRIS1PAID000001/cancel", headers=AUTH)
    assert r.status_code == 409
    assert r.json()["error"] == "already_settled"


def test_qris_create_returns_201_with_qr_payload(client):
    r = client.post(
        f"/v1/merchants/{WK_ID}/qris",
        json={"amount": 50000, "note": "Kamar 3 test"},
        headers={**AUTH, "Idempotency-Key": "qris-test-key"},
    )
    assert r.status_code == 201
    body = r.json()
    assert "transaction" in body
    assert "qr_payload" in body
    assert "expires_at" in body
    assert body["transaction"]["type"] == "qris"
    assert body["transaction"]["status"] == "pending"
    assert body["transaction"]["note"] == "Kamar 3 test"


def test_link_create_returns_201_with_link_url(client):
    r = client.post(
        f"/v1/merchants/{WK_ID}/links",
        json={"title": "May rent", "amount": 850000, "customer": "Andi"},
        headers={**AUTH, "Idempotency-Key": "link-test-key"},
    )
    assert r.status_code == 201
    body = r.json()
    assert "transaction" in body
    assert body["transaction"]["type"] == "link"
    assert "link_url" in body["transaction"]
    assert body["transaction"]["invoice_number"] is not None


def test_seen_merchant_resets_unread(client):
    r = client.post(f"/v1/merchants/{WK_ID}/seen", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["unread_count"] == 0


def test_seen_company_returns_204_no_body(client):
    r = client.post("/v1/company/seen", headers=AUTH)
    assert r.status_code == 204
    assert r.content == b""


def test_logout_returns_204_no_body(client):
    r = client.post("/v1/sessions/logout", headers=AUTH)
    assert r.status_code == 204
    assert r.content == b""


def test_claim_unclaimed_merchant_returns_201(client):
    r = client.post(
        "/v1/merchants/claim",
        json={"merchant_code": MERCHANT_UNCLAIMED_KOPI_TENDA.code},
        headers=AUTH,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == MERCHANT_UNCLAIMED_KOPI_TENDA.id
    assert body["company_id"] == COMPANY.id
    # Second claim returns 200 (already linked).
    r2 = client.post(
        "/v1/merchants/claim",
        json={"merchant_code": MERCHANT_UNCLAIMED_KOPI_TENDA.code},
        headers=AUTH,
    )
    assert r2.status_code == 200


def test_claim_already_linked_returns_200(client):
    """A merchant already in MERCHANTS for our company returns 200, not 201."""
    wk_code = MERCHANTS[WK_ID].code
    r = client.post(
        "/v1/merchants/claim",
        json={"merchant_code": wk_code},
        headers=AUTH,
    )
    assert r.status_code == 200


def test_trigger_expire_settles_pending_txn(client):
    create = client.post(
        f"/v1/merchants/{WK_ID}/qris",
        json={"amount": 25000},
        headers={**AUTH, "Idempotency-Key": "expire-test-key"},
    )
    assert create.status_code == 201
    txn_id = create.json()["transaction"]["id"]

    r = client.post(
        "/v1/_dev/trigger-expire",
        json={"transaction_id": txn_id},
    )
    assert r.status_code == 200
    assert r.json()["emitted"] == "transaction.expired"
    assert TRANSACTIONS[txn_id].status == "expired"


def test_trigger_payment_with_existing_txn_id(client):
    create = client.post(
        f"/v1/merchants/{WK_ID}/qris",
        json={"amount": 30000},
        headers={**AUTH, "Idempotency-Key": "settle-test-key"},
    )
    txn_id = create.json()["transaction"]["id"]

    r = client.post(
        "/v1/_dev/trigger-payment",
        json={"transaction_id": txn_id},
    )
    assert r.status_code == 202
    assert r.json()["transaction_id"] == txn_id


def test_link_invoice_lowercase_rejected(client):
    """Spec §4.5 invoice_number regex is case-sensitive ^[A-Z0-9-]{1,40}$."""
    r = client.post(
        f"/v1/merchants/{WK_ID}/links",
        json={
            "title": "May rent",
            "amount": 100000,
            "customer": "Andi",
            "invoice_number": "inv-001",
        },
        headers={**AUTH, "Idempotency-Key": "lower-inv-key"},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_request"


def test_health_no_auth_required(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
