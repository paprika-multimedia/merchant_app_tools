from models.transaction import Cpm, Payer, Transaction

# Seed transactions: mix of type (qris/link/cpm) and status (paid/pending/expired).
# All belong to Warung Kosan unless noted.

_WK_ID = "mch_01HX3R9WKQF4P2KJ7DZM"
_KP_ID = "mch_01HX3RAKPQ7M3F4P2KJ7E"

SEED_TRANSACTIONS: list[Transaction] = [
    Transaction(
        id="txn_01HX4QRIS1PAID000001",
        merchant_id=_WK_ID,
        type="qris",
        title="QRIS payment",
        ref="PPK-A412-5938",
        amount=50000,
        status="paid",
        customer=None,
        note="Kamar 3 · May rent",
        invoice_number=None,
        link_url=None,
        payer=Payer(masked_phone="+62 812 •••• 1148", issuer_name="BCA Mobile"),
        cpm=None,
        created_at="2025-05-12T14:00:00+07:00",
        paid_at="2025-05-12T14:02:00+07:00",
        expires_at="2025-05-12T14:15:00+07:00",
    ),
    Transaction(
        id="txn_01HX4LINK1PAID000002",
        merchant_id=_WK_ID,
        type="link",
        title="May rent · Room 3",
        ref="PPK-B821-4471",
        amount=850000,
        status="paid",
        customer="Andi",
        note=None,
        invoice_number="INV-WK-20250512-4831",
        link_url="https://paprika.app/pay/wk-may-rent-4f8a",
        payer=None,
        cpm=None,
        created_at="2025-05-11T09:00:00+07:00",
        paid_at="2025-05-11T10:30:00+07:00",
        expires_at="2025-05-12T09:00:00+07:00",
    ),
    Transaction(
        id="txn_01HX4CPM01PAID000003",
        merchant_id=_WK_ID,
        type="cpm",
        title="QRIS · CPM",
        ref="PPK-C933-1872",
        amount=75000,
        status="paid",
        customer=None,
        note=None,
        invoice_number=None,
        link_url=None,
        payer=None,
        # payer_name deliberately omitted per Spec §2.3
        cpm=Cpm(issuer_name="BCA", masked_account="•••• 4021"),
        created_at="2025-05-12T13:00:00+07:00",
        paid_at="2025-05-12T13:01:00+07:00",
        expires_at=None,
    ),
    Transaction(
        id="txn_01HX4QRIS2PEND000004",
        merchant_id=_WK_ID,
        type="qris",
        title="QRIS payment",
        ref="PPK-D144-9921",
        amount=25000,
        status="pending",
        customer=None,
        note=None,
        invoice_number=None,
        link_url=None,
        payer=None,
        cpm=None,
        created_at="2025-05-12T13:55:00+07:00",
        paid_at=None,
        expires_at="2025-05-12T14:10:00+07:00",
    ),
    Transaction(
        id="txn_01HX4LINK2EXPD000005",
        merchant_id=_WK_ID,
        type="link",
        title="April utilities",
        ref="PPK-E291-3847",
        amount=300000,
        status="expired",
        customer="Budi",
        note=None,
        invoice_number="INV-WK-20250501-0012",
        link_url="https://paprika.app/pay/wk-apr-util-e291",
        payer=None,
        cpm=None,
        created_at="2025-05-01T10:00:00+07:00",
        paid_at=None,
        expires_at="2025-05-02T10:00:00+07:00",
    ),
    Transaction(
        id="txn_01HX4QRIS3PAID000006",
        merchant_id=_KP_ID,
        type="qris",
        title="QRIS payment",
        ref="PPK-F382-7731",
        amount=15000,
        status="paid",
        customer=None,
        note=None,
        invoice_number=None,
        link_url=None,
        payer=Payer(masked_phone=None, issuer_name="GoPay"),
        cpm=None,
        created_at="2025-05-12T11:30:00+07:00",
        paid_at="2025-05-12T11:31:00+07:00",
        expires_at="2025-05-12T11:45:00+07:00",
    ),
]

# Mutable in-memory transaction store — keyed by transaction id.
TRANSACTIONS: dict[str, Transaction] = {t.id: t for t in SEED_TRANSACTIONS}

# Counter per merchant per day for invoice-number generation.
# Key: (merchant_id, "YYYYMMDD") → next counter value.
INVOICE_COUNTERS: dict[tuple[str, str], int] = {}

# Track used invoice numbers per merchant to detect collisions.
# Key: (merchant_id, invoice_number) → True
INVOICE_TAKEN: dict[tuple[str, str], bool] = {}
