import asyncio
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from config import CORS_ORIGINS, PORT, RESPONSE_DELAY_MS
from middleware.auth import AuthMiddleware
from middleware.language import LanguageMiddleware
from router import register_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Paprika Backend Simulator",
        description="Local mock API server mirroring the Paprika Merchant App backend contract.",
        version="1.0.0",
    )

    # CORS — permissive for local development (coding-standards hard rule).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Language middleware runs first so the locale is available to auth middleware.
    app.add_middleware(LanguageMiddleware)

    # Auth middleware — validates Bearer token on all authenticated routes.
    app.add_middleware(AuthMiddleware)

    # Artificial response delay — injected here so it applies uniformly.
    if RESPONSE_DELAY_MS > 0:

        @app.middleware("http")
        async def add_delay(request: Request, call_next):  # type: ignore[no-untyped-def]
            response = await call_next(request)
            await asyncio.sleep(RESPONSE_DELAY_MS / 1000.0)
            return response

    register_routes(app)

    return app


app = create_app()

if __name__ == "__main__":
    logger.info("Starting Paprika Backend Simulator on port %d", PORT)
    logger.info("Response delay: %dms  (set RESPONSE_DELAY_MS=0 to disable)", RESPONSE_DELAY_MS)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )
