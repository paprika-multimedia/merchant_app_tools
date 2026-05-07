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
# Mac / Linux / Git Bash
./run.sh

# Windows
run.bat

# Or manually
pip install -r requirements.txt
python main.py
# Server starts on http://localhost:8080
```

---

## Dev Tools — `dev_tools/`

A small folder of stdlib-only Python helpers for poking the running simulator.
Both scripts read `dev_tools/config.json` (base_url, ws_url, session_token,
merchant_id) so URL/merchant only need to be set in one place.

| File | What |
|---|---|
| `dev_tools/config.json` | Shared config: `base_url`, `ws_url`, `session_token`, `merchant_id` |
| `dev_tools/trigger.py` | Interactive menu — pick `1`–`5`, follow prompts |
| `dev_tools/listen.py` | WebSocket listener — auths and prints every event |
| `dev_tools/trigger.{sh,bat}` | Launchers for `trigger.py` |
| `dev_tools/listen.{sh,bat}` | Launchers for `listen.py` |

Typical usage:

```bash
# Terminal 1 — simulator
./run.sh

# Terminal 2 — WS listener (events stream here as they happen)
./dev_tools/listen.sh

# Terminal 3 — trigger menu
./dev_tools/trigger.sh
```

The trigger menu:
```
1) Trigger payment           (asks for amount, settles via WS after delay)
2) Expire pending txn        (asks for transaction id)
3) Fail pending txn          (asks for transaction id + optional reason)
4) Toggle merchant scan_cpm
5) Force-logout device
6) Generate QR image         (scannable PNG saved to dev_tools/output/)
   ├─ a) CPM customer QR      (8 issuers — for the merchant Scan-QRIS flow)
   ├─ b) Company onboarding QR (Kos Pak Harso — for session claim)
   ├─ c) Merchant claim QR    (4 fixture merchants — for add-merchant flow)
   └─ d) Custom payload       (raw text)
```

Edit `dev_tools/config.json` if you run on a different port or want to target a
different merchant. Option 6 also requires the `qrcode[pil]` package, which is
in `requirements.txt`.

---

## Documentation

| File | Responsibility |
|------|---------------|
| `how_to_use.md` | Practical, copy-paste guide for running and triggering |
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

The easiest way to fire dev triggers is the menu CLI in `dev_tools/`:

```bash
./dev_tools/trigger.sh    # Mac / Linux / Git Bash
dev_tools\trigger.bat     # Windows
```

Or the equivalent raw curls:

```bash
# Settle a payment
curl -X POST http://localhost:8080/v1/_dev/trigger-payment \
     -H "Content-Type: application/json" \
     -d '{"merchant_id": "mch_01HX3R9WKQF4P2KJ7DZM", "amount": 50000}'

# Toggle a capability
curl -X POST http://localhost:8080/v1/_dev/trigger-merchant-update \
     -H "Content-Type: application/json" \
     -d '{"merchant_id": "mch_01HX3R9WKQF4P2KJ7DZM", "toggle_scan_cpm": true}'
```

See `how_to_use.md` for the full hands-on walkthrough and `docs/simulator-guide.md` for the endpoint reference.
