import os

PORT: int = int(os.environ.get("PORT", "8080"))

# Artificial latency added to every HTTP response (ms). Set to 0 for snappy testing.
RESPONSE_DELAY_MS: int = int(os.environ.get("RESPONSE_DELAY_MS", "300"))

# Delay before the simulator emits transaction.paid over WS after a dev trigger.
PAYMENT_SETTLE_DELAY_MS: int = int(os.environ.get("PAYMENT_SETTLE_DELAY_MS", "3000"))

# CORS: allow everything for local development.
CORS_ORIGINS: list[str] = ["*"]

# Heartbeat interval (seconds).
WS_HEARTBEAT_SECONDS: int = 25

# Auth-frame timeout (seconds). Client must send auth frame within this window.
WS_AUTH_TIMEOUT_SECONDS: int = 5

# Idempotency key TTL (seconds). Keys expire after 24 hours.
IDEMPOTENCY_TTL_SECONDS: int = 86_400
