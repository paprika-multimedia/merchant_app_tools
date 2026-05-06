from datetime import datetime, timedelta, timezone
from typing import Any

from models.merchant import Merchant
from models.transaction import Transaction


def _now_iso() -> str:
    """Current time as ISO-8601 with the Asia/Jakarta (+07:00) offset."""
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz).isoformat()


def transaction_created_event(transaction: Transaction) -> dict[str, Any]:
    """Build a transaction.created WS event — Spec §5.3."""
    return {
        "event": "transaction.created",
        "ts": _now_iso(),
        "data": transaction.model_dump(by_alias=True, exclude_none=True),
    }


def transaction_paid_event(transaction: Transaction) -> dict[str, Any]:
    """Build a transaction.paid WS event — Spec §5.3.

    payer_name is stripped from cpm block at the Transaction model level
    (the field does not exist on the Cpm Pydantic model), so this is safe.
    """
    return {
        "event": "transaction.paid",
        "ts": _now_iso(),
        "data": transaction.model_dump(by_alias=True, exclude_none=True),
    }


def transaction_expired_event(transaction_id: str, merchant_id: str, expires_at: str) -> dict[str, Any]:
    """Build a transaction.expired WS event — Spec §5.3."""
    return {
        "event": "transaction.expired",
        "ts": _now_iso(),
        "data": {
            "id": transaction_id,
            "merchant_id": merchant_id,
            "expires_at": expires_at,
        },
    }


def transaction_cancelled_event(
    transaction_id: str, merchant_id: str, reason: str | None = None
) -> dict[str, Any]:
    """Build a transaction.cancelled WS event — Spec §5.3."""
    data: dict[str, Any] = {"id": transaction_id, "merchant_id": merchant_id}
    if reason:
        data["reason"] = reason
    return {
        "event": "transaction.cancelled",
        "ts": _now_iso(),
        "data": data,
    }


def transaction_failed_event(transaction_id: str, merchant_id: str, reason: str | None = None) -> dict[str, Any]:
    """Build a transaction.failed WS event — Spec §5.3."""
    data: dict[str, Any] = {"id": transaction_id, "merchant_id": merchant_id}
    if reason:
        data["reason"] = reason
    return {
        "event": "transaction.failed",
        "ts": _now_iso(),
        "data": data,
    }


def merchant_added_event(merchant: Merchant) -> dict[str, Any]:
    """Build a merchant.added WS event — Spec §5.3."""
    return {
        "event": "merchant.added",
        "ts": _now_iso(),
        "data": merchant.model_dump(by_alias=True, exclude_none=True),
    }


def merchant_removed_event(merchant_id: str, name: str) -> dict[str, Any]:
    """Build a merchant.removed WS event — Spec §5.3."""
    return {
        "event": "merchant.removed",
        "ts": _now_iso(),
        "data": {"id": merchant_id, "name": name},
    }


def merchant_updated_event(merchant: Merchant) -> dict[str, Any]:
    """Build a merchant.updated WS event — Spec §5.3."""
    return {
        "event": "merchant.updated",
        "ts": _now_iso(),
        "data": merchant.model_dump(by_alias=True, exclude_none=True),
    }


def device_logged_out_event(device_id: str, reason: str) -> dict[str, Any]:
    """Build a device.logged_out WS event — Spec §5.3."""
    return {
        "event": "device.logged_out",
        "ts": _now_iso(),
        "data": {"device_id": device_id, "reason": reason},
    }


def ping_event() -> dict[str, Any]:
    """Build a heartbeat ping event — Spec §5.1."""
    return {"event": "ping"}
