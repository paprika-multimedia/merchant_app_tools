from models.merchant import Capabilities, Merchant

# Three seeded merchants exercise the important branches per Handoff.md §5:
#   - Warung Kosan (WK) — CPM enabled, full history
#   - Kantin Pagi (KP) — CPM enabled, smaller volume
#   - Gerobak Rica (GR) — CPM disabled, used to verify tile disabling

MERCHANT_WARUNG_KOSAN = Merchant(
    id="mch_01HX3R9WKQF4P2KJ7DZM",
    company_id="cmp_01HX3R8TZMQ4F9P2KJ7D",
    name="Warung Kosan",
    code="WK4F82D19PQ7M3XR9LB4",
    qr_payload="paprika://merchant/WK4F82D19PQ7M3XR9LB4",
    capabilities=Capabilities(scan_cpm=True, cpm_ceiling=2000000),
    today_total=1250000,
    today_count=18,
    month_total=14820000,
    unread_count=2,
    # last_transaction_amount: index 0 % 5 → amounts[0] = 5000 (IDR minor units)
    # last_transaction_at: approx 5 minutes ago (seeded as a fixed recent timestamp)
    last_transaction_amount=5000,
    last_transaction_at="2026-05-04T07:37:00Z",
    created_at="2024-09-12T08:00:00+07:00",
)

MERCHANT_KANTIN_PAGI = Merchant(
    id="mch_01HX3RAKPQ7M3F4P2KJ7E",
    company_id="cmp_01HX3R8TZMQ4F9P2KJ7D",
    name="Kantin Pagi",
    code="KP7M3F4P2KJ7DZQ9WK4F8",
    qr_payload="paprika://merchant/KP7M3F4P2KJ7DZQ9WK4F8",
    capabilities=Capabilities(scan_cpm=True, cpm_ceiling=2000000),
    today_total=375000,
    today_count=6,
    month_total=4250000,
    unread_count=0,
    # last_transaction_amount: index 1 % 5 → amounts[1] = 10000 (IDR minor units)
    # last_transaction_at: approx 1 hour ago
    last_transaction_amount=10000,
    last_transaction_at="2026-05-04T06:42:00Z",
    created_at="2024-10-05T09:00:00+07:00",
)

MERCHANT_GEROBAK_RICA = Merchant(
    id="mch_01HX3RBGRF4P2KJ7DZQ9W",
    company_id="cmp_01HX3R8TZMQ4F9P2KJ7D",
    name="Gerobak Rica",
    code="GR4P2KJ7DZQ9WK4F8M3F4",
    qr_payload="paprika://merchant/GR4P2KJ7DZQ9WK4F8M3F4",
    capabilities=Capabilities(scan_cpm=False, cpm_ceiling=None),
    today_total=0,
    today_count=0,
    month_total=1200000,
    unread_count=0,
    last_transaction_at=None,
    created_at="2025-01-15T10:00:00+07:00",
)

# Unclaimed merchant — exercises the 201 path on POST /v1/merchants/claim
# (Spec §4.2.1). Not visible to GET /merchants until its code is claimed.
MERCHANT_UNCLAIMED_KOPI_TENDA = Merchant(
    id="mch_01HX3RCQUNCLAIMED7DZX",
    company_id=None,
    name="Kopi Tenda",
    code="KT9X2JZQ9PKM3F4R7HD8",
    qr_payload="paprika://merchant/KT9X2JZQ9PKM3F4R7HD8",
    capabilities=Capabilities(scan_cpm=True, cpm_ceiling=2000000),
    today_total=0,
    today_count=0,
    month_total=0,
    unread_count=0,
    last_transaction_at=None,
    created_at="2026-04-22T10:00:00+07:00",
)

# Mutable in-memory merchant registry — keyed by merchant id.
# Handlers mutate this dict (e.g. after /seen, /claim, DELETE).
MERCHANTS: dict[str, Merchant] = {
    MERCHANT_WARUNG_KOSAN.id: MERCHANT_WARUNG_KOSAN,
    MERCHANT_KANTIN_PAGI.id: MERCHANT_KANTIN_PAGI,
    MERCHANT_GEROBAK_RICA.id: MERCHANT_GEROBAK_RICA,
}

# Unclaimed merchants — same shape, but not in MERCHANTS until their code is
# claimed via POST /v1/merchants/claim. Lookup-only fixture.
UNCLAIMED_MERCHANTS: dict[str, Merchant] = {
    MERCHANT_UNCLAIMED_KOPI_TENDA.id: MERCHANT_UNCLAIMED_KOPI_TENDA,
}

# Map merchant code → merchant id, covering both claimed and unclaimed.
MERCHANT_CODE_INDEX: dict[str, str] = {
    **{m.code: m.id for m in MERCHANTS.values()},
    **{m.code: m.id for m in UNCLAIMED_MERCHANTS.values()},
}
