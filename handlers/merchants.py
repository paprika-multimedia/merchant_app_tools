import json
import re

from fastapi import Request
from fastapi.responses import JSONResponse

from fixtures.company import COMPANY
from fixtures.merchants import MERCHANT_CODE_INDEX, MERCHANTS
from middleware.idempotency import check_idempotency, get_device_id, store_idempotency
from middleware.language import get_locale
from models.errors import make_error
from models.merchant import Capabilities, Merchant
from models.requests import MerchantClaimRequest, MerchantDeleteRequest
from websocket.events import merchant_added_event, merchant_removed_event
from websocket.handler import broadcast

_CODE_RE = re.compile(r"^[A-Z0-9]{20}$")


def _normalize_code(raw: str) -> str:
    return re.sub(r"[\s\-]", "", raw).upper()


async def list_merchants(request: Request) -> JSONResponse:
    """GET /v1/merchants — Spec §4.2."""
    merchants = [m.model_dump(by_alias=True, exclude_none=True) for m in MERCHANTS.values()]
    return JSONResponse(status_code=200, content=merchants)


async def get_merchant(request: Request, merchant_id: str) -> JSONResponse:
    """GET /v1/merchants/:id — Spec §4.2."""
    locale = get_locale()
    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))
    return JSONResponse(status_code=200, content=merchant.model_dump(by_alias=True, exclude_none=True))


async def claim_merchant(request: Request) -> JSONResponse:
    """POST /v1/merchants/claim — Spec §4.2.1.

    Idempotency-Key is accepted but not strictly enforced here (only /scan enforces).
    """
    locale = get_locale()
    body_bytes = await request.body()

    idempotency_key = request.headers.get("Idempotency-Key", "")
    device_id = get_device_id(request.headers)

    # Check idempotency cache (if key provided).
    if idempotency_key:
        is_replay, is_mismatch, cached = check_idempotency(idempotency_key, device_id, body_bytes)
        if is_replay:
            if is_mismatch:
                return JSONResponse(status_code=422, content=make_error("idempotency_mismatch", locale))
            return JSONResponse(status_code=cached["status"], content=cached["body"])

    try:
        payload = json.loads(body_bytes)
        data = MerchantClaimRequest(**payload)
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    code = _normalize_code(data.merchant_code)
    if not _CODE_RE.match(code):
        return JSONResponse(status_code=400, content=make_error("invalid_code", locale))

    merchant_id = MERCHANT_CODE_INDEX.get(code)
    if merchant_id is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    # Check if already linked to this company (idempotent → 200).
    if merchant.company_id == COMPANY.id:
        body = merchant.model_dump(by_alias=True, exclude_none=True)
        if idempotency_key:
            store_idempotency(idempotency_key, device_id, body_bytes, 200, body)
        return JSONResponse(status_code=200, content=body)

    # Check if claimed by a different company.
    body_409 = make_error("claimed_elsewhere", locale)
    if idempotency_key:
        store_idempotency(idempotency_key, device_id, body_bytes, 409, body_409)
    return JSONResponse(status_code=409, content=body_409)


async def delete_merchant(request: Request, merchant_id: str) -> JSONResponse:
    """DELETE /v1/merchants/:id — Spec §4.2.2."""
    locale = get_locale()
    body_bytes = await request.body()

    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    try:
        payload = json.loads(body_bytes)
        data = MerchantDeleteRequest(**payload)
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    # Case-insensitive, trimmed name match — Spec §4.2.2.
    if data.confirm_name.strip().lower() != merchant.name.strip().lower():
        return JSONResponse(status_code=422, content=make_error("name_mismatch", locale))

    name = merchant.name
    del MERCHANTS[merchant_id]
    # Remove from code index.
    stale_codes = [c for c, mid in MERCHANT_CODE_INDEX.items() if mid == merchant_id]
    for c in stale_codes:
        del MERCHANT_CODE_INDEX[c]

    # Broadcast merchant.removed to all connected WS clients — Spec §5.3.
    await broadcast(merchant_removed_event(merchant_id, name))

    return JSONResponse(status_code=204, content=None)


async def seen_merchant(request: Request, merchant_id: str) -> JSONResponse:
    """POST /v1/merchants/:id/seen — Spec §4.2, resets unread_count."""
    locale = get_locale()
    merchant = MERCHANTS.get(merchant_id)
    if merchant is None:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    # Replace with unread_count=0 by rebuilding the model (Pydantic models are immutable).
    updated = merchant.model_copy(update={"unread_count": 0})
    MERCHANTS[merchant_id] = updated

    return JSONResponse(status_code=200, content=updated.model_dump(by_alias=True, exclude_none=True))


async def get_company(request: Request) -> JSONResponse:
    """GET /v1/company — Spec §4.1."""
    return JSONResponse(
        status_code=200,
        content=COMPANY.model_dump(by_alias=True, exclude_none=True),
    )


async def seen_company(request: Request) -> JSONResponse:
    """POST /v1/company/seen — Spec §4.1, resets unread_count on all merchants."""
    for mid, merchant in list(MERCHANTS.items()):
        MERCHANTS[mid] = merchant.model_copy(update={"unread_count": 0})
    return JSONResponse(status_code=200, content=None)
