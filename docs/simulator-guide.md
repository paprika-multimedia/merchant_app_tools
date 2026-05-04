# Backend Simulator — Implementation Guide

> **For:** agents and developers building this mock API server.
> **Purpose:** Enable full Flutter app development without a live backend.

---

## What It Does

The simulator implements the API contract defined in `Spec.md` using fixture data that matches the JSX prototype's mock objects. It enables:

- Full Flutter app development without a real backend
- WebSocket event testing (payment notifications, merchant updates)
- Idempotency validation on CPM endpoints
- Localized error messages
- Realistic delays for loading-state testing

---

## Project Structure

```
backend_simulator/
  main.py                       // Entry point, starts uvicorn server
  config.py                     // Port, CORS origins, mock delays
  router.py                     // Route registration
  middleware/
    auth.py                     // Bearer token validation (mock)
    language.py                 // Accept-Language parsing → context
    idempotency.py              // Idempotency-Key validation + replay
  handlers/
    sessions.py                 // POST /sessions/claim, /sessions/refresh
    merchants.py                // GET /merchants, POST /merchants/claim, DELETE
    transactions.py             // POST /merchants/:id/qris, /links, /scan
    dev_triggers.py             // Dev-only: trigger WS events for testing
  models/                       // Pydantic models mirroring Spec.md §2
    company.py
    merchant.py
    transaction.py
    errors.py
    requests.py
  websocket/
    handler.py                  // WebSocket with auth-frame protocol
    events.py                   // Event builders: transaction.paid, merchant.updated
  fixtures/
    company.py                  // "Kos Pak Harso" (matches JSX COMPANY)
    merchants.py                // Merchants with capabilities
    transactions.py             // Mix of types and statuses
  requirements.txt
```

---

## Endpoints to Implement

Reference: `Spec.md` §4.

### Sessions

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/sessions/claim` | Body: `{ company_code }` → returns session + refresh tokens |
| POST | `/v1/sessions/refresh` | Body: `{ refresh_token }` → rotates tokens (single-use) |

### Merchants

| Method | Path | Notes |
|--------|------|-------|
| GET | `/v1/merchants` | List all merchants for the session's company |
| GET | `/v1/merchants/:id` | Single merchant with today_total, today_count, etc. |
| POST | `/v1/merchants/claim` | Body: `{ merchant_code }` — client sends Idempotency-Key (not strictly enforced) |
| DELETE | `/v1/merchants/:id` | Remove merchant |
| POST | `/v1/merchants/:id/seen` | Mark notifications as read (decrement unread_count) |

### Transactions

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/merchants/:id/qris` | Create Dynamic QRIS — client sends Idempotency-Key (not strictly enforced) |
| POST | `/v1/merchants/:id/links` | Create Payment Link — client sends Idempotency-Key (not strictly enforced) |
| POST | `/v1/merchants/:id/scan` | CPM charge — Idempotency-Key REQUIRED (400 if missing) |
| GET | `/v1/merchants/:id/transactions` | List transactions (paginated with cursor) |
| GET | `/v1/transactions/:id` | Single transaction |

### WebSocket

| Method | Path | Notes |
|--------|------|-------|
| WS | `/v1/stream` | Auth-frame protocol, emits events |

### Dev-Only (not in Spec.md — for testing)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/_dev/trigger-payment` | Body: `{ merchant_id, amount }` → emits `transaction.paid` after delay |
| POST | `/v1/_dev/trigger-merchant-update` | Body: `{ merchant_id }` → emits `merchant.updated` |

---

## Fixture Data

Mock data should match the JSX prototype for consistency:

**Company:** "Kos Pak Harso" with code `A4F28K19PQ7M3XR9LB42`

**Merchants:**
- "Warung Kosan" — `scan_cpm: true`, `cpm_ceiling: 2000000`, active transactions
- "Kamar 3" — `scan_cpm: false`, fewer transactions

**Transactions:** Mix of types (qris, link, cpm) and statuses (paid, pending, expired)

---

## WebSocket Protocol

1. Client connects to `/v1/stream`
2. Client sends: `{ "type": "auth", "token": "<session_token>" }`
3. Server validates token (any non-empty = valid in simulator), responds: `{ "type": "auth.ok" }`
4. Server sends events when triggered:
   - `{ "type": "transaction.paid", "data": { "id": "txn_...", "merchant_id": "mch_...", "amount": 50000, ... } }`
   - `{ "type": "merchant.updated", "data": { "id": "mch_...", "capabilities": {...}, ... } }`
5. Server sends heartbeat ping every 25 seconds

---

## Idempotency Handling

Per `Spec.md` §8, the four mutating endpoints (`/merchants/claim`, `/merchants/:id/qris`, `/merchants/:id/links`, `/merchants/:id/scan`) accept an `Idempotency-Key` header. The client MUST send one on all four; the server only strictly enforces it on `/scan`.

- Store idempotency keys in an in-memory dict keyed by `(device_id, idempotency_key)`: `{ key: (status_code, response_body, body_sha256) }`
- On duplicate key with matching body: return the cached response (same status, same body)
- On duplicate key with different body (SHA-256 of canonicalized JSON differs): return `422 idempotency_mismatch`
- Keys expire after 24 hours (or server restart)
- Missing key on `/merchants/:id/scan`: return `400 idempotency_required`
- Missing key on the other three mutating endpoints: log warning but proceed (the spec only requires enforcement on `/scan`)

---

## Error Responses

Follow Spec.md §11 format:

```json
{
  "error": {
    "code": "not_found",
    "message": "Merchant tidak ditemukan"
  }
}
```

Localize `message` based on `Accept-Language` header:
- `id` → Indonesian message
- `en` → English message
- Missing/unrecognized → default to `id`

Common error codes to implement:
- `not_found` — resource doesn't exist
- `unauthenticated` — missing/invalid token (401)
- `capability_disabled` — scan_cpm is off for this merchant (403)
- `idempotency_required` — missing key on CPM (400)
- `validation_error` — bad request body (422)
- `rate_limited` — too many requests (429)

---

## Configurable Delays

Add artificial latency for testing loading states in the Flutter app:

```python
# config.py
RESPONSE_DELAY_MS = 300  # Default delay on all responses
PAYMENT_SETTLE_DELAY_MS = 3000  # Delay before emitting transaction.paid via WS
```

Set via environment variables to override:
```bash
RESPONSE_DELAY_MS=0 python main.py  # No delay for fast testing
```

---

## Recommended Packages

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
websockets>=12.0
pydantic>=2.5.0
python-multipart>=0.0.6
```
