import json

from fastapi import Request
from fastapi.responses import JSONResponse

from middleware.language import get_locale
from models.errors import make_error
from models.requests import PushRegisterRequest


async def register_push(request: Request) -> JSONResponse:
    """POST /v1/devices/me/push — Spec §4.7. Simulator accepts and ignores push tokens."""
    locale = get_locale()
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes)
        PushRegisterRequest(**payload)
    except Exception:
        return JSONResponse(status_code=400, content=make_error("invalid_request", locale))
    return JSONResponse(status_code=200, content={"registered": True})


async def unregister_push(request: Request) -> JSONResponse:
    """DELETE /v1/devices/me/push — Spec §4.7. Simulator no-ops."""
    return JSONResponse(status_code=204, content=None)
