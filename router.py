from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse

from handlers.dev_triggers import trigger_merchant_update, trigger_payment
from handlers.devices import register_push, unregister_push
from handlers.merchants import (
    claim_merchant,
    delete_merchant,
    get_company,
    get_merchant,
    list_merchants,
    seen_company,
    seen_merchant,
)
from handlers.sessions import claim_session, logout_session, refresh_session
from handlers.transactions import (
    cancel_transaction,
    create_link,
    create_qris,
    get_transaction,
    list_transactions,
    scan_cpm,
)
from websocket.handler import ws_endpoint


def register_routes(app: FastAPI) -> None:
    """Register all API routes on the FastAPI app instance.

    All route paths are defined here and only here — handlers must not hardcode paths.
    """

    # --- Sessions ---
    app.add_api_route("/v1/sessions/claim", claim_session, methods=["POST"])
    app.add_api_route("/v1/sessions/refresh", refresh_session, methods=["POST"])
    app.add_api_route("/v1/sessions/logout", logout_session, methods=["POST"])

    # --- Company ---
    app.add_api_route("/v1/company", get_company, methods=["GET"])
    app.add_api_route("/v1/company/seen", seen_company, methods=["POST"])

    # --- Merchants ---
    app.add_api_route("/v1/merchants", list_merchants, methods=["GET"])
    # /merchants/claim must come before /merchants/{merchant_id} to avoid path conflict.
    app.add_api_route("/v1/merchants/claim", claim_merchant, methods=["POST"])
    app.add_api_route("/v1/merchants/{merchant_id}", get_merchant, methods=["GET"])
    app.add_api_route("/v1/merchants/{merchant_id}", delete_merchant, methods=["DELETE"])
    app.add_api_route("/v1/merchants/{merchant_id}/seen", seen_merchant, methods=["POST"])

    # --- Transactions (merchant-scoped creation) ---
    app.add_api_route("/v1/merchants/{merchant_id}/qris", create_qris, methods=["POST"])
    app.add_api_route("/v1/merchants/{merchant_id}/links", create_link, methods=["POST"])
    app.add_api_route("/v1/merchants/{merchant_id}/scan", scan_cpm, methods=["POST"])
    app.add_api_route("/v1/merchants/{merchant_id}/transactions", list_transactions, methods=["GET"])

    # --- Transactions (global) ---
    app.add_api_route("/v1/transactions/{transaction_id}", get_transaction, methods=["GET"])
    app.add_api_route("/v1/transactions/{transaction_id}/cancel", cancel_transaction, methods=["POST"])

    # --- Devices / push ---
    app.add_api_route("/v1/devices/me/push", register_push, methods=["POST"])
    app.add_api_route("/v1/devices/me/push", unregister_push, methods=["DELETE"])

    # --- WebSocket ---
    app.add_api_websocket_route("/v1/stream", ws_endpoint)

    # --- Dev triggers (not in Spec — for testing only) ---
    app.add_api_route("/v1/_dev/trigger-payment", trigger_payment, methods=["POST"])
    app.add_api_route("/v1/_dev/trigger-merchant-update", trigger_merchant_update, methods=["POST"])

    # Health check — handy during Flutter dev.
    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(status_code=200, content={"status": "ok"})
