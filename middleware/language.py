from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Request-scoped locale variable. Handlers read this to pick error message language.
request_locale: ContextVar[str] = ContextVar("request_locale", default="id")


class LanguageMiddleware(BaseHTTPMiddleware):
    """Parse Accept-Language header and set the request-scoped locale context."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        raw = request.headers.get("Accept-Language", "")
        # Collapse BCP-47 subtags: "id-ID" → "id", "en-US" → "en".
        tag = raw.split(",")[0].split(";")[0].strip().split("-")[0].lower()
        locale = "en" if tag == "en" else "id"
        token = request_locale.set(locale)
        try:
            response = await call_next(request)
        finally:
            request_locale.reset(token)
        return response


def get_locale() -> str:
    """Return the locale for the current request. Defaults to 'id'."""
    return request_locale.get()
