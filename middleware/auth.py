from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from middleware.language import get_locale
from models.errors import make_error

# Paths that do NOT require a Bearer token.
UNAUTHENTICATED_PATHS: frozenset[str] = frozenset(
    {
        "/v1/sessions/claim",
        "/v1/sessions/refresh",
    }
)

# WebSocket path — auth happens via first frame, not HTTP header.
WS_PATH = "/v1/stream"


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate Bearer token on every authenticated request.

    The simulator accepts any non-empty token as valid (Spec §3 — mock only).
    Real auth is not implemented; this gate just ensures the Flutter app is
    exercising the header correctly.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path

        # WebSocket upgrades and unauthenticated endpoints skip the check.
        if path == WS_PATH or path in UNAUTHENTICATED_PATHS or path.startswith("/_dev") or path.startswith("/v1/_dev"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or not auth_header[7:].strip():
            locale = get_locale()
            return JSONResponse(
                status_code=401,
                content=make_error("unauthenticated", locale),
            )

        return await call_next(request)
