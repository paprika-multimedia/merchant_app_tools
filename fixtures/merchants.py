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
    last_transaction_at="2025-05-12T14:02:00+07:00",
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
    last_transaction_at="2025-05-12T11:30:00+07:00",
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

# Mutable in-memory merchant registry — keyed by merchant id.
# Handlers mutate this dict (e.g. after /seen, /claim, DELETE).
MERCHANTS: dict[str, Merchant] = {
    MERCHANT_WARUNG_KOSAN.id: MERCHANT_WARUNG_KOSAN,
    MERCHANT_KANTIN_PAGI.id: MERCHANT_KANTIN_PAGI,
    MERCHANT_GEROBAK_RICA.id: MERCHANT_GEROBAK_RICA,
}

# Map merchant code → merchant id for the claim flow.
MERCHANT_CODE_INDEX: dict[str, str] = {
    m.code: m.id for m in MERCHANTS.values()
}
