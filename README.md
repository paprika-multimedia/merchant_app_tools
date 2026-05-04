# Paprika Merchant — Backend Simulator

> Local mock API server so the Flutter app can be developed without a live backend.
> Returns fixture data matching the JSX prototype.

---

## Requirements

- **Python 3.11 or newer**
- pip
- A free port (default 8080)

---

## Quick Start

```bash
pip install -r requirements.txt
python main.py
# Server starts on http://localhost:8080
```

---

## Documentation

| File | Responsibility |
|------|---------------|
| `docs/file-index.md` | Quick file lookup — find any file by responsibility |
| `docs/coding-standards.md` | Python-specific coding rules and conventions |
| `docs/simulator-guide.md` | Full implementation guide: endpoints, WebSocket, fixtures |

Also read the shared standards at `../docs/coding-standards.md`.

---

## Tech Stack

- **FastAPI** — async web framework
- **uvicorn** — ASGI server
- **websockets** — WebSocket support
- **Pydantic v2** — request/response models

---

## What It Does

- Implements all API endpoints from `Spec.md` §4 with fixture data
- Supports auth-frame WebSocket protocol for realtime events
- Caches `Idempotency-Key` for replay-safety on mutating endpoints; strictly enforces (400 if missing) only on `/merchants/:id/scan`
- Returns localized error messages based on `Accept-Language`
- Provides a dev trigger endpoint for testing payment notifications

---

## Key Commands

```bash
# Run server
python main.py

# Run with custom port
PORT=9090 python main.py

# Disable artificial latency (snappier tests)
RESPONSE_DELAY_MS=0 python main.py

# Run tests
pytest
```

---

## Testing Against the Flutter App

Once the server is running, point the Flutter app at it:

```bash
flutter run --dart-define=API_BASE_URL=http://localhost:8080/v1 \
            --dart-define=WS_URL=ws://localhost:8080/v1/stream
```

Trigger a payment notification end-to-end (emits `transaction.paid` over WS to any connected client):

```bash
curl -X POST http://localhost:8080/v1/_dev/trigger-payment \
     -H "Content-Type: application/json" \
     -d '{"merchant_id": "mch_warung_kosan", "amount": 50000}'
```

Trigger a merchant capability change (emits `merchant.updated`):

```bash
curl -X POST http://localhost:8080/v1/_dev/trigger-merchant-update \
     -H "Content-Type: application/json" \
     -d '{"merchant_id": "mch_warung_kosan"}'
```

See `docs/simulator-guide.md` for the full endpoint reference.
