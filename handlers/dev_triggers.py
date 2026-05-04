import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from config import PAYMENT_SETTLE_DELAY_MS
from fixtures.merchants import MERCHANTS
from fixtures.transactions import TRANSACTIONS
from models.transaction import Cpm, Payer, Transaction
from websocket.events import merchant_updated_event, transaction_paid_event
from websocket.handler import broadcast


def _now_jakarta() -> str:
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz).isoformat()


def _new_txn_id() -> str:
    return "txn_" + uuid.uuid4().hex[:20].upper()


def _new_ref() -> str:
    parts = [uuid.uuid4().hex[:4].upper() for _ in range(2)]
    return f"PPK-{parts[0]}-{parts[1]}"


async def _settle_after_delay(txn: Transaction) -> None:
    """Wait PAYMENT_SETTLE_DELAY_MS then emit transaction.paid."""
    await asyncio.sleep(PAYMENT_SETTLE_DELAY_MS / 1000.0)
    paid = txn.model_copy(
        update={
            "status": "paid",
            "paid_at": _now_jakarta(),
            "payer": Payer(masked_phone="+62 812 •••• 9988", issuer_name="BCA Mobile"),
        }
    )
    TRANSACTIONS[txn.id] = paid
    await broadcast(transaction_paid_event(paid))


async def trigger_payment(request: Request) -> JSONResponse:
    """POST /v1/_dev/trigger-payment — creates a pending QRIS and settles it via WS.

    Body: { "merchant_id": "...", "amount": 50000 }
    Emits transaction.paid after PAYMENT_SETTLE_DELAY_MS.
    """
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
        merchant_id = payload["merchant_id"]
        amount = int(payload["amount"])
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid_request", "message": "Bad body"})

    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content={"error": "not_found", "message": "Merchant not found"})

    txn_id = _new_txn_id()
    txn = Transaction(
        id=txn_id,
        merchant_id=merchant_id,
        type="qris",
        title="QRIS payment",
        ref=_new_ref(),
        amount=amount,
        status="pending",
        created_at=_now_jakarta(),
        expires_at=None,
    )
    TRANSACTIONS[txn_id] = txn

    # Fire-and-forget: settle after configured delay.
    asyncio.get_event_loop().create_task(_settle_after_delay(txn))

    return JSONResponse(
        status_code=202,
        content={
            "transaction_id": txn_id,
            "message": f"Payment will settle in {PAYMENT_SETTLE_DELAY_MS}ms via WebSocket",
        },
    )


async def trigger_merchant_update(request: Request) -> JSONResponse:
    """POST /v1/_dev/trigger-merchant-update — emits merchant.updated immediately.

    Body: { "merchant_id": "..." }
    Optionally toggles scan_cpm capability for manual testing.
    """
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
        merchant_id = payload["merchant_id"]
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid_request", "message": "Bad body"})

    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content={"error": "not_found", "message": "Merchant not found"})

    # Optional: toggle scan_cpm so the Flutter dev can test capability-change flow.
    toggle = payload.get("toggle_scan_cpm", False)
    if toggle:
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
