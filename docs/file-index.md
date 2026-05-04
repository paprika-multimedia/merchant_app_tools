# Backend Simulator — File Index

> **Purpose:** Quick-lookup map so agents can grab the right file without searching.
> If the file you need isn't listed here, then search the codebase manually.

---

## Project Root

| Path | Responsibility |
|------|---------------|
| `README.md` | Project setup, run commands, quick orientation |
| `requirements.txt` | Python dependencies |
| `main.py` | Entry point — starts uvicorn server |
| `config.py` | Port, CORS origins, mock delays |
| `router.py` | Route registration (all endpoints wired here) |
| `docs/` | All project-specific documentation |

---

## Middleware

| Path | Responsibility |
|------|---------------|
| `middleware/auth.py` | Bearer token validation (mock — accepts any non-empty token) |
| `middleware/language.py` | Parse `Accept-Language` header → set context locale |
| `middleware/idempotency.py` | Validate & cache Idempotency-Key; return cached responses on replay |

---

## Handlers (Route Implementations)

| Path | Responsibility |
|------|---------------|
| `handlers/sessions.py` | `POST /sessions/claim` — return mock session token |
| | `POST /sessions/refresh` — rotate token (mock) |
| `handlers/merchants.py` | `GET /merchants` — list fixture merchants |
| | `GET /merchants/:id` — single merchant with stats |
| | `POST /merchants/claim` — claim by code |
| | `DELETE /merchants/:id` — remove merchant |
| | `POST /merchants/:id/seen` — mark as read |
| `handlers/transactions.py` | `POST /merchants/:id/qris` — create Dynamic QRIS |
| | `POST /merchants/:id/links` — create Payment Link |
| | `POST /merchants/:id/scan` — CPM charge (requires Idempotency-Key) |
| | `GET /merchants/:id/transactions` — list (paginated) |
| | `GET /transactions/:id` — single transaction |

---

## Models (Pydantic)

| Path | Responsibility |
|------|---------------|
| `models/company.py` | Company schema (Spec §2.1) |
| `models/merchant.py` | Merchant + Capabilities schema (Spec §2.2) |
| `models/transaction.py` | Transaction schema (Spec §2.3) |
| `models/errors.py` | Error response shape (Spec §11) |
| `models/requests.py` | Request body schemas (claim, qris, link, scan) |

---

## WebSocket

| Path | Responsibility |
|------|---------------|
| `websocket/handler.py` | WS endpoint at `/v1/stream` — auth-frame protocol |
| `websocket/events.py` | Event builders: `transaction.paid`, `merchant.updated` |

---

## Fixtures (Mock Data)

| Path | Responsibility |
|------|---------------|
| `fixtures/company.py` | "Kos Pak Harso" — matches JSX prototype |
| `fixtures/merchants.py` | "Warung Kosan" (scan_cpm: true), "Kamar 3" (scan_cpm: false) |
| `fixtures/transactions.py` | Mix of qris/link/cpm, paid/pending/expired |

---

## Dev-Only Endpoints

| Path | Responsibility |
|------|---------------|
| `handlers/dev_triggers.py` | `POST /v1/_dev/trigger-payment` — emits `transaction.paid` via WS |
| | `POST /v1/_dev/trigger-merchant-update` — emits `merchant.updated` via WS |
