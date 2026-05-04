import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from config import PAYMENT_SETTLE_DELAY_MS
from fixtures.merchants import MERCHANTS
from fixtures.transactions import TRANSACTIONS
from middleware.language import get_locale
from models.errors import make_error
from models.transaction import Payer, Transaction
from websocket.events import (
    device_logged_out_event,
    merchant_updated_event,
    transaction_expired_event,
    transaction_failed_event,
    transaction_paid_event,
)
from websocket.handler import broadcast

# UTC ISO-8601 with Z suffix, matching the Spec §1 convention for
# last_transaction_at stored on the Merchant resource.
def _now_utc_z() -> str:
    from datetime import timezone as _tz
    return datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_jakarta() -> str:
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz).isoformat()


def _new_txn_id() -> str:
    return "txn_" + uuid.uuid4().hex[:20].upper()


def _new_ref() -> str:
    parts = [uuid.uuid4().hex[:4].upper() for _ in range(2)]
    return f"PPK-{parts[0]}-{parts[1]}"


async def _settle_after_delay(txn_id: str) -> None:
    """Wait PAYMENT_SETTLE_DELAY_MS then emit transaction.paid for txn_id.

    After settling, updates the owning merchant's last_transaction_amount and
    last_transaction_at so that GET /merchants reflects the most recent payment,
    then broadcasts merchant.updated — Spec §5.3 / §10.
    """
    await asyncio.sleep(PAYMENT_SETTLE_DELAY_MS / 1000.0)
    current = TRANSACTIONS.get(txn_id)
    if current is None or current.status != "pending":
        return

    paid_at = _now_utc_z()
    paid = current.model_copy(
        update={
            "status": "paid",
            "paid_at": paid_at,
            "payer": Payer(masked_phone="+62 812 •••• 9988", issuer_name="BCA Mobile"),
        }
    )
    TRANSACTIONS[txn_id] = paid
    await broadcast(transaction_paid_event(paid))

    # Update merchant last-tx fields — Spec §10 (webhooks) requires atomic update
    # of last_transaction_at; we extend that to also track last_transaction_amount.
    merchant = MERCHANTS.get(paid.merchant_id)
    if merchant is not None:
        updated_merchant = merchant.model_copy(
            update={
                "last_transaction_amount": paid.amount,
                "last_transaction_at": paid_at,
            }
        )
        MERCHANTS[paid.merchant_id] = updated_merchant
        await broadcast(merchant_updated_event(updated_merchant))


async def trigger_payment(request: Request) -> JSONResponse:
    """POST /v1/_dev/trigger-payment — settle a pending txn (or create one).

    Body:
      { "transaction_id": "txn_..." }                    → settle existing pending txn
      { "merchant_id": "...", "amount": 50000 }          → create + settle a fresh QRIS

    Emits transaction.paid after PAYMENT_SETTLE_DELAY_MS.
    """
    locale = get_locale()
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    txn_id = payload.get("transaction_id")
    if txn_id:
        existing = TRANSACTIONS.get(txn_id)
        if existing is None:
            return JSONResponse(status_code=404, content=make_error("not_found", locale))
        if existing.status != "pending":
            return JSONResponse(status_code=409, content=make_error("already_settled", locale))
        asyncio.get_event_loop().create_task(_settle_after_delay(txn_id))
        return JSONResponse(
            status_code=202,
            content={
                "transaction_id": txn_id,
                "message": f"Existing pending transaction will settle in {PAYMENT_SETTLE_DELAY_MS}ms via WebSocket",
            },
        )

    try:
        merchant_id = payload["merchant_id"]
        amount = int(payload["amount"])
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    if MERCHANTS.get(merchant_id) is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    new_id = _new_txn_id()
    txn = Transaction(
        id=new_id,
        merchant_id=merchant_id,
        type="qris",
        title="QRIS payment",
        ref=_new_ref(),
        amount=amount,
        status="pending",
        created_at=_now_jakarta(),
        expires_at=None,
    )
    TRANSACTIONS[new_id] = txn

    asyncio.get_event_loop().create_task(_settle_after_delay(new_id))

    return JSONResponse(
        status_code=202,
        content={
            "transaction_id": new_id,
            "message": f"Payment will settle in {PAYMENT_SETTLE_DELAY_MS}ms via WebSocket",
        },
    )


async def trigger_merchant_update(request: Request) -> JSONResponse:
    """POST /v1/_dev/trigger-merchant-update — emits merchant.updated immediately.

    Body: { "merchant_id": "...", "toggle_scan_cpm": false }
    """
    locale = get_locale()
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
        merchant_id = payload["merchant_id"]
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    if payload.get("toggle_scan_cpm", False):
        new_caps = merchant.capabilities.model_copy(
            update={"scan_cpm": not merchant.capabilities.scan_cpm}
        )
        merchant = merchant.model_copy(update={"capabilities": new_caps})
        MERCHANTS[merchant_id] = merchant

    await broadcast(merchant_updated_event(merchant))

    return JSONResponse(
        status_code=200,
        content={"merchant_id": merchant_id, "emitted": "merchant.updated"},
    )


async def trigger_expire(request: Request) -> JSONResponse:
    """POST /v1/_dev/trigger-expire — expires a pending txn and emits transaction.expired."""
    locale = get_locale()
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
        txn_id = payload["transaction_id"]
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    txn = TRANSACTIONS.get(txn_id)
    if txn is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))
    if txn.status != "pending":
        return JSONResponse(status_code=409, content=make_error("already_settled", locale))

    expired = txn.model_copy(update={"status": "expired"})
    TRANSACTIONS[txn_id] = expired
    await broadcast(
        transaction_expired_event(txn_id, txn.merchant_id, txn.expires_at or _now_jakarta())
    )
    return JSONResponse(
        status_code=200,
        content={"transaction_id": txn_id, "emitted": "transaction.expired"},
    )


async def trigger_fail(request: Request) -> JSONResponse:
    """POST /v1/_dev/trigger-fail — fails a pending txn and emits transaction.failed."""
    locale = get_locale()
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
        txn_id = payload["transaction_id"]
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    reason = payload.get("reason")
    txn = TRANSACTIONS.get(txn_id)
    if txn is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))
    if txn.status != "pending":
        return JSONResponse(status_code=409, content=make_error("already_settled", locale))

    failed = txn.model_copy(update={"status": "failed"})
    TRANSACTIONS[txn_id] = failed
    await broadcast(transaction_failed_event(txn_id, txn.merchant_id, reason))
    return JSONResponse(
        status_code=200,
        content={"transaction_id": txn_id, "emitted": "transaction.failed"},
    )


async def trigger_logout(request: Request) -> JSONResponse:
    """POST /v1/_dev/trigger-logout — emits device.logged_out to all connected WS clients.

    Body: { "device_id": "...", "reason": "remote_revoke" } (both optional)
    """
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes) if body_bytes else {}
    except Exception:
        payload = {}

    device_id = payload.get("device_id", "dev_01HX3RCMQ4F9P2KJ7DZR")
    reason = payload.get("reason", "remote_revoke")
    await broadcast(device_logged_out_event(device_id, reason))
    return JSONResponse(
        status_code=200,
        content={"device_id": device_id, "emitted": "device.logged_out"},
    )
