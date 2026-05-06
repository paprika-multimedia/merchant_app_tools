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

### Merchant IDs (already linked to the fixture company)

| Name | ID | `scan_cpm` |
|---|---|---|
| Warung Kosan | `mch_01HX3R9WKQF4P2KJ7DZM` | on |
| Kantin Pagi | `mch_01HX3RAKPQ7M3F4P2KJ7E` | on |
| Gerobak Rica | `mch_01HX3RBGRF4P2KJ7DZQ9W` | off (CPM disabled) |

### Unclaimed merchant code (for `POST /v1/merchants/claim`)

| Name | Merchant code | Result on first claim |
|---|---|---|
| Kopi Tenda | `KT9X2JZQ9PKM3F4R7HD8` | `201 Created` + `merchant.added` over WS |

---

## 3a. The easy way — `dev_tools/`

Two stdlib-only scripts share a single config file (`dev_tools/config.json`)
and remove the need to type curl commands:

| Script | What it does |
|---|---|
| `dev_tools/trigger.{sh,bat,py}` | Interactive menu (`1`–`5`), prompts for amount / txn id |
| `dev_tools/listen.{sh,bat,py}` | Connects to WS, sends auth frame, prints every event |

`dev_tools/config.json` controls them both:
```json
{
  "base_url": "http://localhost:8080",
  "ws_url": "ws://localhost:8080/v1/stream",
  "session_token": "mock_session_token_30d",
  "merchant_id": "mch_01HX3R9WKQF4P2KJ7DZM"
}
```

Typical three-terminal flow:

```bash
# Terminal 1 — server
./run.sh

# Terminal 2 — listen for events
./dev_tools/listen.sh

# Terminal 3 — fire triggers from the menu
./dev_tools/trigger.sh
```

The trigger menu:
```
1) Trigger payment           (asks for amount, settles via WS after delay)
2) Expire pending txn        (asks for transaction id)
3) Fail pending txn          (asks for transaction id + optional reason)
4) Toggle merchant scan_cpm
5) Force-logout device
q) Quit
```

If you change the simulator port or want to target a different merchant, edit
`dev_tools/config.json` once — both scripts pick it up.

---

## 4. Dev triggers — overview

The simulator exposes endpoints under `/v1/_dev/` for manual testing. They are
**not** in the API spec; they exist so you can fake real-world events during
development. None of them require a Bearer token.

| Endpoint | Emits over WS | Useful for |
|---|---|---|
| `POST /v1/_dev/trigger-payment` | `transaction.paid` (after delay) | "Payment received" notification flow |
| `POST /v1/_dev/trigger-merchant-update` | `merchant.updated` (immediate) | Capability changes (e.g. CPM toggle) |
| `POST /v1/_dev/trigger-expire` | `transaction.expired` (immediate) | Expired-payment UI on a pending txn |
| `POST /v1/_dev/trigger-fail` | `transaction.failed` (immediate) | CPM decline / payment failure UI |
| `POST /v1/_dev/trigger-logout` | `device.logged_out` (immediate) | Forced-logout flow on the device |

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
  "event": "transaction.paid",
  "ts": "2026-05-04T14:00:00+07:00",
  "data": {
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
  "event": "merchant.updated",
  "ts": "2026-05-04T14:00:00+07:00",
  "data": { "id": "mch_...", "capabilities": { "scan_cpm": false, "cpm_ceiling": null }, "...": "..." }
}
```

---

## 7. Other dev triggers

### Expire a pending transaction

```bash
curl -X POST http://localhost:8080/v1/_dev/trigger-expire \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"txn_..."}'
```
Marks the txn `expired` and emits `transaction.expired`. 409 if already settled.

### Fail a pending transaction

```bash
curl -X POST http://localhost:8080/v1/_dev/trigger-fail \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"txn_...","reason":"insufficient_funds"}'
```
Marks the txn `failed` and emits `transaction.failed` (with `reason` if supplied).

### Force-logout the device

```bash
curl -X POST http://localhost:8080/v1/_dev/trigger-logout \
  -H "Content-Type: application/json" \
  -d '{"reason":"remote_revoke"}'
```
Emits `device.logged_out` to all connected WS clients. The Flutter app should
clear its session and bounce to login.

### Settle an existing pending transaction (instead of creating one)

```bash
curl -X POST http://localhost:8080/v1/_dev/trigger-payment \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"txn_..."}'
```
Useful for testing the QRIS flow end-to-end: create a dynamic QR from the app,
copy the returned `id`, then settle it from a separate terminal.

---

## 8. End-to-end: drive the Flutter app

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

## 9. Troubleshooting

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

## 10. Run the test suite

```bash
pytest -q
```

Idempotency, error localisation, wire shapes, WS events, and handler
integration. All should pass before you trust the simulator.
