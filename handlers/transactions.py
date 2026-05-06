import json
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from fixtures.merchants import MERCHANTS
from fixtures.transactions import INVOICE_COUNTERS, INVOICE_TAKEN, TRANSACTIONS
from middleware.idempotency import check_idempotency, get_device_id, store_idempotency
from middleware.language import get_locale
from models.errors import make_error
from models.requests import LinkCreateRequest, QrisCreateRequest, ScanRequest
from models.transaction import Cpm, Transaction
from websocket.events import transaction_cancelled_event, transaction_created_event
from websocket.handler import broadcast

_INVOICE_NUMBER_RE = re.compile(r"^[A-Z0-9\-]{1,40}$")

# Supported CPM issuers in the simulator.
_SUPPORTED_ISSUERS = {"BCA", "Mandiri", "BRI", "BNI", "GoPay", "OVO", "Dana", "ShopeePay"}


def _now_jakarta() -> str:
    """Current time formatted as ISO-8601 with +07:00 offset."""
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz).isoformat()


def _now_plus(minutes: int = 0, hours: int = 0) -> str:
    tz = timezone(timedelta(hours=7))
    delta = timedelta(minutes=minutes, hours=hours)
    return (datetime.now(tz) + delta).isoformat()


def _new_txn_id() -> str:
    return "txn_" + uuid.uuid4().hex[:20].upper()


def _new_ref() -> str:
    parts = [uuid.uuid4().hex[:4].upper() for _ in range(2)]
    return f"PPK-{parts[0]}-{parts[1]}"


def _next_invoice_number(merchant_id: str) -> str:
    tz = timezone(timedelta(hours=7))
    day_str = datetime.now(tz).strftime("%Y%m%d")
    key = (merchant_id, day_str)
    count = INVOICE_COUNTERS.get(key, 0) + 1
    INVOICE_COUNTERS[key] = count
    short_id = merchant_id[-4:].upper()
    return f"INV-{short_id}-{day_str}-{count:04d}"


def _parse_qris_issuer(qr_payload: str) -> str | None:
    """Very simplified QRIS payload parser for the simulator.

    A real implementation validates the TLV CRC; here we just extract a plausible
    issuer name from the payload string for fixture purposes.
    """
    for issuer in _SUPPORTED_ISSUERS:
        if issuer.upper() in qr_payload.upper():
            return issuer
    return "BCA"


async def create_qris(request: Request, merchant_id: str) -> JSONResponse:
    """POST /v1/merchants/:id/qris — Spec §4.4."""
    locale = get_locale()
    body_bytes = await request.body()

    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    idempotency_key = request.headers.get("Idempotency-Key", "")
    device_id = get_device_id(request.headers)

    if idempotency_key:
        is_replay, is_mismatch, cached = check_idempotency(idempotency_key, device_id, body_bytes)
        if is_replay:
            if is_mismatch:
                return JSONResponse(status_code=422, content=make_error("idempotency_mismatch", locale))
            return JSONResponse(status_code=cached["status"], content=cached["body"])

    try:
        payload = json.loads(body_bytes)
        data = QrisCreateRequest(**payload)
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    if data.amount <= 0:
        return JSONResponse(status_code=400, content=make_error("amount_too_low", locale))

    txn_id = _new_txn_id()
    expires_at = _now_plus(minutes=15)
    txn = Transaction(
        id=txn_id,
        merchant_id=merchant_id,
        type="qris",
        title="QRIS payment",
        ref=_new_ref(),
        amount=data.amount,
        status="pending",
        note=data.note,
        created_at=_now_jakarta(),
        expires_at=expires_at,
    )
    TRANSACTIONS[txn_id] = txn

    response_body = {
        "transaction": txn.model_dump(by_alias=True, exclude_none=True),
        "qr_payload": f"00020101021226680014ID.CO.PAPRIKA.SIM0118{merchant_id[:16]}5204000053033605802ID5925{merchant.name[:25]}6013Jakarta Pusat6304ABCD",
        "qr_image_url": f"https://api.paprika.app/v1/qris/{txn_id}.svg",
        "expires_at": expires_at,
    }

    if idempotency_key:
        store_idempotency(idempotency_key, device_id, body_bytes, 201, response_body)

    await broadcast(transaction_created_event(txn))

    return JSONResponse(status_code=201, content=response_body)


async def create_link(request: Request, merchant_id: str) -> JSONResponse:
    """POST /v1/merchants/:id/links — Spec §4.5."""
    locale = get_locale()
    body_bytes = await request.body()

    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    idempotency_key = request.headers.get("Idempotency-Key", "")
    device_id = get_device_id(request.headers)

    if idempotency_key:
        is_replay, is_mismatch, cached = check_idempotency(idempotency_key, device_id, body_bytes)
        if is_replay:
            if is_mismatch:
                return JSONResponse(status_code=422, content=make_error("idempotency_mismatch", locale))
            return JSONResponse(status_code=cached["status"], content=cached["body"])

    try:
        payload = json.loads(body_bytes)
        data = LinkCreateRequest(**payload)
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    if data.amount <= 0:
        return JSONResponse(status_code=400, content=make_error("amount_too_low", locale))

    # Invoice number handling — Spec §4.5 (case-sensitive ^[A-Z0-9-]{1,40}$).
    if data.invoice_number:
        inv = data.invoice_number.strip()
        if not _INVOICE_NUMBER_RE.match(inv):
            return JSONResponse(status_code=400, content=make_error("invalid_request", locale))
        if INVOICE_TAKEN.get((merchant_id, inv)):
            return JSONResponse(status_code=409, content=make_error("invoice_taken", locale))
        invoice_number = inv
    else:
        invoice_number = _next_invoice_number(merchant_id)

    INVOICE_TAKEN[(merchant_id, invoice_number)] = True

    txn_id = _new_txn_id()
    slug = re.sub(r"[^a-z0-9]", "-", data.title.lower())[:20]
    link_url = f"https://paprika.app/pay/{merchant_id[-4:].lower()}-{slug}-{txn_id[-4:].lower()}"
    expires_at = _now_plus(hours=24)

    txn = Transaction(
        id=txn_id,
        merchant_id=merchant_id,
        type="link",
        title=data.title,
        ref=_new_ref(),
        amount=data.amount,
        status="pending",
        customer=data.customer,
        invoice_number=invoice_number,
        link_url=link_url,
        created_at=_now_jakarta(),
        expires_at=expires_at,
    )
    TRANSACTIONS[txn_id] = txn

    response_body = {
        "transaction": txn.model_dump(by_alias=True, exclude_none=True),
        "expires_at": expires_at,
    }

    if idempotency_key:
        store_idempotency(idempotency_key, device_id, body_bytes, 201, response_body)

    await broadcast(transaction_created_event(txn))

    return JSONResponse(status_code=201, content=response_body)


async def scan_cpm(request: Request, merchant_id: str) -> JSONResponse:
    """POST /v1/merchants/:id/scan — Spec §4.6.

    Idempotency-Key is REQUIRED on this endpoint — returns 400 if missing.
    """
    locale = get_locale()
    body_bytes = await request.body()

    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    # Capability gate — Spec §4.6.
    if not merchant.capabilities.scan_cpm:
        return JSONResponse(
            status_code=403,
            content={**make_error("capability_disabled", locale), "capability": "scan_cpm"},
        )

    # Idempotency-Key is required for CPM — Spec §8.
    idempotency_key = request.headers.get("Idempotency-Key", "")
    if not idempotency_key:
        return JSONResponse(status_code=400, content=make_error("idempotency_required", locale))

    device_id = get_device_id(request.headers)
    is_replay, is_mismatch, cached = check_idempotency(idempotency_key, device_id, body_bytes)
    if is_replay:
        if is_mismatch:
            return JSONResponse(status_code=422, content=make_error("idempotency_mismatch", locale))
        return JSONResponse(status_code=cached["status"], content=cached["body"])

    try:
        payload = json.loads(body_bytes)
        data = ScanRequest(**payload)
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    # Amount validation — Spec §4.6.
    if data.amount < 1000:
        return JSONResponse(status_code=400, content=make_error("amount_too_low", locale))

    ceiling = merchant.capabilities.cpm_ceiling or 2_000_000
    if data.amount > ceiling:
        return JSONResponse(status_code=400, content=make_error("amount_too_high", locale))

    # QR payload validation (simplified for simulator).
    qr = data.qr_payload.strip()
    if not qr or len(qr) < 10:
        return JSONResponse(status_code=400, content=make_error("invalid_qr", locale))

    issuer = _parse_qris_issuer(qr)

    txn_id = _new_txn_id()
    txn = Transaction(
        id=txn_id,
        merchant_id=merchant_id,
        type="cpm",
        title="QRIS · CPM",
        ref=_new_ref(),
        amount=data.amount,
        status="pending",
        # payer_name is NEVER included in mobile responses — Spec §2.3.
        cpm=Cpm(issuer_name=issuer, masked_account="•••• 4021"),
        created_at=_now_jakarta(),
    )
    TRANSACTIONS[txn_id] = txn

    response_body = {"transaction": txn.model_dump(by_alias=True, exclude_none=True)}

    store_idempotency(idempotency_key, device_id, body_bytes, 201, response_body)

    await broadcast(transaction_created_event(txn))

    return JSONResponse(status_code=201, content=response_body)


async def list_transactions(request: Request, merchant_id: str) -> JSONResponse:
    """GET /v1/merchants/:id/transactions — Spec §4.3, paginated newest-first."""
    locale = get_locale()

    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    params = request.query_params
    limit = min(int(params.get("limit", "20")), 100)
    cursor = params.get("cursor", None)
    status_filter = params.get("status", None)
    type_filter = params.get("type", None)

    all_txns = [t for t in TRANSACTIONS.values() if t.merchant_id == merchant_id]
    # Sort newest first by created_at.
    all_txns.sort(key=lambda t: t.created_at, reverse=True)

    if status_filter:
        all_txns = [t for t in all_txns if t.status == status_filter]
    if type_filter:
        all_txns = [t for t in all_txns if t.type == type_filter]

    # Cursor is the last id seen; start from the item after it.
    if cursor:
        ids = [t.id for t in all_txns]
        try:
            start = ids.index(cursor) + 1
        except ValueError:
            start = 0
        all_txns = all_txns[start:]

    page = all_txns[:limit]
    next_cursor = page[-1].id if len(all_txns) > limit else None

    return JSONResponse(
        status_code=200,
        content={
            "data": [t.model_dump(by_alias=True, exclude_none=True) for t in page],
            "next_cursor": next_cursor,
        },
    )


async def get_transaction(request: Request, transaction_id: str) -> JSONResponse:
    """GET /v1/transactions/:id — Spec §4.3.1."""
    locale = get_locale()
    txn = TRANSACTIONS.get(transaction_id)
    if txn is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))
    return JSONResponse(status_code=200, content=txn.model_dump(by_alias=True, exclude_none=True))


async def cancel_transaction(request: Request, transaction_id: str) -> JSONResponse:
    """POST /v1/transactions/:id/cancel — Spec §4.3.2."""
    locale = get_locale()
    body_bytes = await request.body()

    txn = TRANSACTIONS.get(transaction_id)
    if txn is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    if txn.status != "pending":
        return JSONResponse(status_code=409, content=make_error("already_settled", locale))

    idempotency_key = request.headers.get("Idempotency-Key", "")
    device_id = get_device_id(request.headers)

    if idempotency_key:
        is_replay, is_mismatch, cached = check_idempotency(idempotency_key, device_id, body_bytes)
        if is_replay:
            if is_mismatch:
                return JSONResponse(status_code=422, content=make_error("idempotency_mismatch", locale))
            return JSONResponse(status_code=cached["status"], content=cached["body"])

    reason: str | None = None
    if body_bytes:
        try:
            parsed = json.loads(body_bytes)
            if isinstance(parsed, dict):
                raw_reason = parsed.get("reason")
                if isinstance(raw_reason, str) and raw_reason.strip():
                    reason = raw_reason.strip()
        except Exception:
            reason = None

    cancelled = txn.model_copy(update={"status": "cancelled"})
    TRANSACTIONS[transaction_id] = cancelled

    body = cancelled.model_dump(by_alias=True, exclude_none=True)
    if idempotency_key:
        store_idempotency(idempotency_key, device_id, body_bytes, 200, body)

    await broadcast(transaction_cancelled_event(transaction_id, txn.merchant_id, reason))

    return JSONResponse(status_code=200, content=body)
