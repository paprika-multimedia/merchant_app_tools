"""Unit tests for WebSocket event builder shapes — Spec §5.3."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.merchant import Capabilities, Merchant
from models.transaction import Cpm, Transaction
from websocket.events import (
    merchant_updated_event,
    ping_event,
    transaction_created_event,
    transaction_paid_event,
    transaction_cancelled_event,
    transaction_failed_event,
    transaction_expired_event,
    merchant_added_event,
    merchant_removed_event,
    device_logged_out_event,
)


def _make_txn(**kwargs) -> Transaction:
    defaults = dict(
        id="txn_test",
        merchant_id="mch_test",
        type="qris",
        title="QRIS payment",
        ref="PPK-TEST-0001",
        amount=50000,
        status="pending",
        created_at="2025-01-01T00:00:00+07:00",
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def _make_merchant(**kwargs) -> Merchant:
    defaults = dict(
        id="mch_test",
        company_id="cmp_test",
        name="Warung",
        code="WK4F82D19PQ7M3XR9LB4",
        qr_payload="paprika://merchant/WK4F82D19PQ7M3XR9LB4",
        capabilities=Capabilities(scan_cpm=True, cpm_ceiling=2000000),
        today_total=0,
        today_count=0,
        month_total=0,
        unread_count=0,
        created_at="2025-01-01T00:00:00+07:00",
    )
    defaults.update(kwargs)
    return Merchant(**defaults)


def test_transaction_created_event_shape():
    evt = transaction_created_event(_make_txn())
    assert evt["event"] == "transaction.created"
    assert "ts" in evt
    assert "data" in evt
    assert evt["data"]["id"] == "txn_test"


def test_transaction_paid_event_has_no_payer_name():
    txn = _make_txn(
        type="cpm",
        status="paid",
        cpm=Cpm(issuer_name="BCA", masked_account="•••• 4021"),
    )
    evt = transaction_paid_event(txn)
    assert evt["event"] == "transaction.paid"
    # payer_name must not appear anywhere in the event payload.
    assert "payer_name" not in str(evt)


def test_transaction_expired_event_shape():
    evt = transaction_expired_event("txn_exp", "mch_x", "2025-01-01T00:15:00+07:00")
    assert evt["event"] == "transaction.expired"
    assert evt["data"]["id"] == "txn_exp"
    assert evt["data"]["merchant_id"] == "mch_x"
    assert "expires_at" in evt["data"]


def test_transaction_cancelled_event_shape():
    evt = transaction_cancelled_event("txn_can", "mch_x")
    assert evt["event"] == "transaction.cancelled"
    assert evt["data"]["id"] == "txn_can"
    assert evt["data"]["merchant_id"] == "mch_x"


def test_transaction_failed_event_shape():
    evt = transaction_failed_event("txn_fail", "mch_x", reason="declined")
    assert evt["event"] == "transaction.failed"
    assert evt["data"]["reason"] == "declined"


def test_merchant_added_event_shape():
    evt = merchant_added_event(_make_merchant())
    assert evt["event"] == "merchant.added"
    assert evt["data"]["id"] == "mch_test"


def test_merchant_removed_event_shape():
    evt = merchant_removed_event("mch_del", "Warung Kosan")
    assert evt["event"] == "merchant.removed"
    assert evt["data"]["name"] == "Warung Kosan"


def test_merchant_updated_event_shape():
    evt = merchant_updated_event(_make_merchant())
    assert evt["event"] == "merchant.updated"
    assert "capabilities" in evt["data"]


def test_device_logged_out_event_shape():
    evt = device_logged_out_event("dev_001", "admin_action")
    assert evt["event"] == "device.logged_out"
    assert evt["data"]["device_id"] == "dev_001"
    assert evt["data"]["reason"] == "admin_action"


def test_ping_event_shape():
    evt = ping_event()
    assert evt["event"] == "ping"
