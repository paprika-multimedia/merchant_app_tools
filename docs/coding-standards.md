# Backend Simulator — Python Coding Standards

> **Applies to:** all Python code in `backend_simulator/`.
> **Read also:** `../../docs/coding-standards.md` for shared principles that apply to both projects.

---

## Python-Specific Conventions

### Naming

```
Files:         snake_case.py
Classes:       PascalCase (including Pydantic models)
Variables:     snake_case
Constants:     UPPER_SNAKE_CASE
Functions:     snake_case
Endpoints:     Match Spec.md paths exactly (e.g., /v1/merchants/{id}/qris)
Models:        PascalCase matching Spec.md resource names (Company, Merchant, Transaction)
```

### Code Style

- Python 3.11+ features are allowed (match statement, `type` alias, etc.)
- Use type hints on ALL function signatures — parameters and return types.
- Use `async def` for ALL route handlers (even if not awaiting — keeps consistency).
- Maximum line length: 100 characters.
- Imports ordered: stdlib → third-party → local.

### Pydantic Models

- One model per file in `models/`.
- Use `model_config = ConfigDict(populate_by_name=True)` for JSON alias support.
- Use `Field(alias="...")` to match Spec.md snake_case field names.
- All response models should have examples in their schema (helps with auto-docs).

### Handler Rules

- Keep handlers thin: validate input, call fixture/logic, return response.
- Business logic (if any) goes in separate utility functions.
- Always return proper HTTP status codes matching Spec.md §11.
- Localize error messages based on request context locale.

### Fixture Data

- Fixtures are plain Python dicts/dataclasses.
- No database — everything is in-memory, reset on server restart.
- Fixture data MUST match the JSX prototype's mock objects for consistency.
- Use mutable state (module-level dicts) for idempotency cache and transaction lists.

### Error Handling

- All errors follow Spec.md §11 shape: `{ "error": { "code": "...", "message": "..." } }`
- Localize `message` based on `Accept-Language` header.
- Use FastAPI's `HTTPException` with a custom exception handler for the error shape.
- Never return a bare string or unstructured error.

### WebSocket

- Auth-frame protocol: first message must be `{ "type": "auth", "token": "..." }`.
- Respond with `{ "type": "auth.ok" }` on valid token.
- Send heartbeat ping every 25 seconds.
- Track connected clients for event broadcasting.

---

## Hard Rules (Simulator-Specific)

1. **Every endpoint in Spec.md §4 must be implemented** — even if it just returns fixture data.
2. **Idempotency-Key validation on CPM** — `POST /merchants/:id/scan` returns `400 idempotency_required` if the header is missing.
3. **Accept-Language determines error message language** — always check the header.
4. **CORS must be permissive** — allow all origins for local development.
5. **Configurable delays** — responses should have optional artificial latency for loading-state testing.
6. **No real authentication** — accept any non-empty Bearer token as valid.
7. **Dev trigger endpoints** — must exist for testing payment notifications and merchant updates.
8. **WebSocket events must include all fields** from Spec.md §5 — the Flutter app parses them.
