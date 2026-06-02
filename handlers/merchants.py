import json
import re

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from fixtures.company import COMPANY
from fixtures.merchants import (
    MERCHANT_CODE_INDEX,
    MERCHANTS,
    UNCLAIMED_MERCHANTS,
)
from middleware.idempotency import (
    check_idempotency,
    get_device_id,
    store_idempotency,
)
from middleware.language import get_locale
from models.errors import make_error
from models.requests import MerchantClaimRequest, MerchantDeleteRequest
from websocket.events import merchant_added_event, merchant_removed_event
from websocket.handler import broadcast

_CODE_RE = re.compile(r"^[A-Z0-9]{20,}$")


def _normalize_code(raw: str) -> str:
    return re.sub(r"[\s\-]", "", raw).upper()


async def list_merchants(request: Request) -> JSONResponse:
    """GET /v1/merchants — Spec §4.2."""
    merchants = [
        m.model_dump(by_alias=True, exclude_none=True)
        for m in MERCHANTS.values()
    ]

    return JSONResponse(
        status_code=200,
        content=merchants,
    )


async def get_merchant(
    request: Request,
    merchant_id: str,
) -> JSONResponse:
    """GET /v1/merchants/:id — Spec §4.2."""

    locale = get_locale()

    merchant = MERCHANTS.get(merchant_id)

    if merchant is None:
        return JSONResponse(
            status_code=404,
            content=make_error("not_found", locale),
        )

    return JSONResponse(
        status_code=200,
        content=merchant.model_dump(
            by_alias=True,
            exclude_none=True,
        ),
    )


async def claim_merchant(request: Request) -> JSONResponse:
    """POST /v1/merchants/claim — Spec §4.2.1."""

    locale = get_locale()
    body_bytes = await request.body()

    idempotency_key = request.headers.get("Idempotency-Key", "")
    device_id = get_device_id(request.headers)

    # Optional idempotency replay handling.
    if idempotency_key:
        is_replay, is_mismatch, cached = check_idempotency(
            idempotency_key,
            device_id,
            body_bytes,
        )

        if is_replay:
            if is_mismatch:
                return JSONResponse(
                    status_code=422,
                    content=make_error(
                        "idempotency_mismatch",
                        locale,
                    ),
                )

            return JSONResponse(
                status_code=cached["status"],
                content=cached["body"],
            )

    # Parse request body.
    try:
        payload = json.loads(body_bytes)
        data = MerchantClaimRequest(**payload)

    except Exception:
        return JSONResponse(
            status_code=400,
            content=make_error("invalid_request", locale),
        )

    # Normalize scanned code.
    code = _normalize_code(data.merchant_code)

    print("RAW CODE =", data.merchant_code)
    print("NORMALIZED CODE =", code)
    print("CODE INDEX =", MERCHANT_CODE_INDEX)

    # Validate code format.
    if not _CODE_RE.match(code):
        return JSONResponse(
            status_code=400,
            content=make_error("invalid_code", locale),
        )

    # FIX:
    # lookup merchant id via MERCHANT_CODE_INDEX
    merchant_id = MERCHANT_CODE_INDEX.get(code)

    print("MERCHANT ID =", merchant_id)

    if merchant_id is None:
        return JSONResponse(
            status_code=404,
            content=make_error("not_found", locale),
        )

    # Already claimed by current company.
    claimed = MERCHANTS.get(merchant_id)

    if claimed is not None:
        if claimed.company_id == COMPANY.id:
            body = claimed.model_dump(
                by_alias=True,
                exclude_none=True,
            )

            if idempotency_key:
                store_idempotency(
                    idempotency_key,
                    device_id,
                    body_bytes,
                    200,
                    body,
                )

            return JSONResponse(
                status_code=200,
                content=body,
            )

        # Claimed by another company.
        body_409 = make_error(
            "claimed_elsewhere",
            locale,
        )

        if idempotency_key:
            store_idempotency(
                idempotency_key,
                device_id,
                body_bytes,
                409,
                body_409,
            )

        return JSONResponse(
            status_code=409,
            content=body_409,
        )

    # Merchant exists in unclaimed pool.
    pending = UNCLAIMED_MERCHANTS.get(merchant_id)

    if pending is not None:
        linked = pending.model_copy(
            update={
                "company_id": COMPANY.id,
            }
        )

        MERCHANTS[merchant_id] = linked

        del UNCLAIMED_MERCHANTS[merchant_id]

        body = linked.model_dump(
            by_alias=True,
            exclude_none=True,
        )

        if idempotency_key:
            store_idempotency(
                idempotency_key,
                device_id,
                body_bytes,
                201,
                body,
            )

        await broadcast(
            merchant_added_event(linked)
        )

        return JSONResponse(
            status_code=201,
            content=body,
        )

    return JSONResponse(
        status_code=404,
        content=make_error("not_found", locale),
    )


async def delete_merchant(
    request: Request,
    merchant_id: str,
) -> JSONResponse:
    """DELETE /v1/merchants/:id — Spec §4.2.2."""

    locale = get_locale()
    body_bytes = await request.body()

    merchant = MERCHANTS.get(merchant_id)

    if merchant is None:
        return JSONResponse(
            status_code=404,
            content=make_error("not_found", locale),
        )

    try:
        payload = json.loads(body_bytes)
        data = MerchantDeleteRequest(**payload)

    except Exception:
        return JSONResponse(
            status_code=400,
            content=make_error("invalid_request", locale),
        )

    if (
        data.confirm_name.strip().lower()
        != merchant.name.strip().lower()
    ):
        return JSONResponse(
            status_code=422,
            content=make_error(
                "name_mismatch",
                locale,
            ),
        )

    name = merchant.name

    del MERCHANTS[merchant_id]

    stale_codes = [
        c
        for c, mid in MERCHANT_CODE_INDEX.items()
        if mid == merchant_id
    ]

    for c in stale_codes:
        del MERCHANT_CODE_INDEX[c]

    await broadcast(
        merchant_removed_event(
            merchant_id,
            name,
        )
    )

    return Response(status_code=204)


async def seen_merchant(
    request: Request,
    merchant_id: str,
) -> JSONResponse:
    """POST /v1/merchants/:id/seen."""

    locale = get_locale()

    merchant = MERCHANTS.get(merchant_id)

    if merchant is None:
        return JSONResponse(
            status_code=404,
            content=make_error("not_found", locale),
        )

    updated = merchant.model_copy(
        update={
            "unread_count": 0,
        }
    )

    MERCHANTS[merchant_id] = updated

    return JSONResponse(
        status_code=200,
        content=updated.model_dump(
            by_alias=True,
            exclude_none=True,
        ),
    )


async def get_company(
    request: Request,
) -> JSONResponse:
    """GET /v1/company — Spec §4.1."""

    return JSONResponse(
        status_code=200,
        content=COMPANY.model_dump(
            by_alias=True,
            exclude_none=True,
        ),
    )


async def seen_company(
    request: Request,
) -> Response:
    """POST /v1/company/seen."""

    for mid, merchant in list(MERCHANTS.items()):
        MERCHANTS[mid] = merchant.model_copy(
            update={
                "unread_count": 0,
            }
        )

    return Response(status_code=204)