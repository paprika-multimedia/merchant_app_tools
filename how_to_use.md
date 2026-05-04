# How To Use the Backend Simulator

A practical, copy-paste guide for running the simulator and firing dev triggers.
Read this if you just want to *use* the simulator. For architecture and the full
endpoint reference, see `docs/simulator-guide.md`.

---

## 1. Run the server

### Option A — launcher scripts (recommended)

The launchers `cd` into this folder, install/refresh dependencies, then start
the server. Any extra arguments and environment variables are forwarded.

**Windows (cmd / PowerShell):**
```
run.bat
```

**macOS / Linux / Git Bash:**
```bash
./run.sh
```

### Option B — manual

```bash
pip install -r requirements.txt
python main.py
```

### What you should see

```
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Sanity check from another terminal:
```bash
curl http://localhost:8080/health
# {"status":"ok"}
```

---

## 2. Configuration via environment variables

| Variable | Default | Effect |
|---|---|---|
| `PORT` | `8080` | HTTP/WS port |
| `RESPONSE_DELAY_MS` | `300` | Artificial latency on every HTTP response. Set `0` for snappy local tests. |
| `PAYMENT_SETTLE_DELAY_MS` | `3000` | How long the simulator waits before emitting `transaction.paid` after a dev trigger. |

Examples:

```bash
# Snappy mode, alternate port
PORT=9090 RESPONSE_DELAY_MS=0 ./run.sh
```

```cmd
REM Windows cmd
set PORT=9090
set RESPONSE_DELAY_MS=0
run.bat
```

---

## 3. Fixture credentials

These are the values the simulator recognises out of the box. Use them when
claiming a session, listing merchants, or firing triggers.

| What | Value |
|---|---|
| Company code (for `POST /v1/sessions/claim`) | `A4F28K19PQ7M3XR9LB42` |
| Mock session token (for `Authorization: Bearer ...`) | `mock_session_token_30d` |
| WebSocket URL | `ws://localhost:8080/v1/stream` |

### Merchant IDs

| Name | ID | `scan_cpm` |
|---|---|---|
| Warung Kosan | `mch_01HX3R9WKQF4P2KJ7DZM` | on |
| Kantin Pagi | `mch_01HX3RAKPQ7M3F4P2KJ7E` | on |
| Gerobak Rica | `mch_01HX3RBGRF4P2KJ7DZQ9W` | off (CPM disabled) |

---

## 4. Dev triggers — overview

The simulator exposes two endpoints under `/v1/_dev/` for manual testing.
They are **not** in the API spec; they exist so you can fake real-world events
during development.

| Endpoint | Emits over WS | Useful for |
|---|---|---|
| `POST /v1/_dev/trigger-payment` | `transaction.paid` (after delay) | Testing the "Payment received" notification flow |
| `POST /v1/_dev/trigger-merchant-update` | `merchant.updated` (immediate) | Testing capability changes (e.g. CPM toggle) |

> WebSocket events are only delivered to **currently connected** clients. If
> nothing is listening, the trigger still succeeds but no client sees it.

---

## 5. Trigger a payment notification

This is the most common trigger — it simulates a customer paying a QRIS code.

### Step 1. Connect a WebSocket client

The simulator requires an auth frame within 5 s of connect, otherwise it closes
with code `4401`.

**Easiest path: run the Flutter app.** It connects automatically once you log in.

**Manual path with [websocat](https://github.com/vi/websocat):**
```bash
websocat ws://localhost:8080/v1/stream
```
Immediately paste:
```json
{"type":"auth","token":"mock_session_token_30d"}
```
You should receive periodic heartbeat frames every ~25 s.

### Step 2. Fire the trigger

```bash
curl -X POST http://localhost:8080/v1/_dev/trigger-payment \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"mch_01HX3R9WKQF4P2KJ7DZM","amount":50000}'
```

Response (immediate):
```json
{
  "transaction_id": "txn_XXXXXXXXXXXXXXXXXXXX",
  "message": "Payment will settle in 3000ms via WebSocket"
}
```

After `PAYMENT_SETTLE_DELAY_MS` (default 3 s), every connected WS client
receives:
```json
{
  "type": "transaction.paid",
  "transaction": {
    "id": "txn_XXXXXXXXXXXXXXXXXXXX",
    "merchant_id": "mch_01HX3R9WKQF4P2KJ7DZM",
    "type": "qris",
    "amount": 50000,
    "status": "paid",
    "paid_at": "...",
    "payer": { "masked_phone": "+62 812 •••• 9988", "issuer_name": "BCA Mobile" }
  }
}
```

The Flutter app turns this WS event into the on-device "Payment received"
notification and updates the dashboard.

---

## 6. Trigger a merchant capability change

Useful for testing how the app reacts when CPM is toggled remotely.

```bash
curl -X POST http://localhost:8080/v1/_dev/trigger-merchant-update \
  -H "Content-Type: application/json" \
  -d '{
        "merchant_id": "mch_01HX3R9WKQF4P2KJ7DZM",
        "toggle_scan_cpm": true
      }'
```

- Without `toggle_scan_cpm`: emits `merchant.updated` with current state.
- With `toggle_scan_cpm: true`: flips the CPM capability *and* emits the event.

Connected WS clients receive:
```json
{
  "type": "merchant.updated",
  "merchant": { "...": "...", "capabilities": { "scan_cpm": false, "cpm_ceiling": null } }
}
```

---

## 7. End-to-end: drive the Flutter app

```bash
# Terminal 1 — simulator
cd backend_simulator
./run.sh

# Terminal 2 — Flutter, pointed at the simulator
cd merchant_app
flutter run \
  --dart-define=API_BASE_URL=http://localhost:8080/v1 \
  --dart-define=WS_URL=ws://localhost:8080/v1/stream

# Terminal 3 — fire a payment whenever you want a notification
curl -X POST http://localhost:8080/v1/_dev/trigger-payment \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"mch_01HX3R9WKQF4P2KJ7DZM","amount":75000}'
```

When onboarding asks for a company code, paste `A4F28K19PQ7M3XR9LB42`.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| WS closes with `4401` immediately | No auth frame sent in time | Send `{"type":"auth","token":"mock_session_token_30d"}` within 5 s of connecting |
| WS closes with `4400` | Bad/missing token in auth frame | Use the mock token above |
| `404 not_found` from a trigger | Wrong `merchant_id` | Use one of the IDs in the table in §3 |
| Trigger returns 202 but app shows nothing | No WS client was connected at the time | Make sure the Flutter app is in foreground, or connect with websocat |
| `403 capability_disabled` on `/scan` | Merchant has `scan_cpm: false` | Use a CPM-enabled merchant, or toggle it on with `trigger-merchant-update` |
| `400 idempotency_required` on `/scan` | Missing `Idempotency-Key` header | Add `-H "Idempotency-Key: $(uuidgen)"` |
| Port 8080 already in use | Another process holding the port | `PORT=9090 ./run.sh` |

---

## 9. Run the test suite

```bash
pytest -q
```

44 tests across idempotency, error localisation, wire shapes, WS events, and
handler integration. All should pass before you trust the simulator.
