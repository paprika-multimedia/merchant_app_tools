import json
import re

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from fixtures.company import COMPANY
from fixtures.merchants import MERCHANTS
from middleware.language import get_locale
from models.errors import make_error
from models.requests import SessionClaimRequest, SessionRefreshRequest

# 20-char alphanumeric uppercase code pattern — Spec §6.3.
_CODE_RE = re.compile(r"^[A-Z0-9]{20}$")

# Mock token values. In the simulator, any non-empty token is valid.
_MOCK_SESSION_TOKEN = "mock_session_token_30d"
_MOCK_REFRESH_TOKEN = "mock_refresh_token_90d"
_MOCK_DEVICE_ID = "dev_01HX3RCMQ4F9P2KJ7DZR"


def _normalize_code(raw: str) -> str:
    """Strip whitespace and hyphens, uppercase — Spec §6.3 normalization."""
    return re.sub(r"[\s\-]", "", raw).upper()


async def claim_session(request: Request) -> JSONResponse:
    """POST /v1/sessions/claim — Spec §3.1."""
    locale = get_locale()

    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
        data = SessionClaimRequest(**payload)
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    code = _normalize_code(data.company_code)
    if not _CODE_RE.match(code):
        return JSONResponse(status_code=400, content=make_error("invalid_code", locale))

    if code != COMPANY.code:
        return JSONResponse(status_code=404, content=make_error("not_found", locale))

    merchants_list = [m.model_dump(by_alias=True, exclude_none=True) for m in MERCHANTS.values()]

    return JSONResponse(
        status_code=200,
        content={
            "session_token": _MOCK_SESSION_TOKEN,
            "refresh_token": _MOCK_REFRESH_TOKEN,
            "device_id": _MOCK_DEVICE_ID,
            "company": COMPANY.model_dump(by_alias=True, exclude_none=True),
            "merchants": merchants_list,
        },
    )


async def refresh_session(request: Request) -> JSONResponse:
    """POST /v1/sessions/refresh — Spec §3.1.1."""
    locale = get_locale()

    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
        data = SessionRefreshRequest(**payload)
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))

    if not data.refresh_token:
        return JSONResponse(status_code=401, content=make_error("refresh_revoked", locale))

    # Simulator: rotate tokens unconditionally for any non-empty refresh_token.
    return JSONResponse(
        status_code=200,
        content={
            "session_token": _MOCK_SESSION_TOKEN,
            "refresh_token": _MOCK_REFRESH_TOKEN,
        },
    )


async def logout_session(request: Request) -> Response:
    """POST /v1/sessions/logout — Spec §3.2."""
    # Simulator: nothing to revoke. Return 204 with no body.
    return Response(status_code=204)
