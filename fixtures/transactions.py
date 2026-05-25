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

# Generate 200 deterministic dummy transactions to simulate active transaction history
import random
from datetime import datetime, timedelta, timezone

_rng = random.Random(42)
_base_time = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone(timedelta(hours=7)))

_issuers = ["BCA Mobile", "GoPay", "OVO", "Dana", "LinkAja", "ShopeePay", "Mandiri Livin", "BRImo"]
_customers = ["Andi", "Budi", "Cici", "Dedi", "Evi", "Feri", "Gita", "Heri", "Ira", "Joko", "Rian", "Santi", "Tono", "Umi", "Vina"]
_notes = [
    "Kopi Susu Gula Aren", "Nasi Goreng Spesial", "Sewa Kamar Kost", 
    "Indomie Rebus Double", "Es Teh Manis", "Roti Bakar Cokelat", 
    "Sate Ayam 1 Porsi", "Cemilan Keripik", "Laundry Kiloan", "Aqua Gelas"
]

for i in range(1, 201):
    # Spread transactions chronologically, roughly every 3 hours
    minutes_ago = i * 180 + _rng.randint(-45, 45)
    created_dt = _base_time - timedelta(minutes=minutes_ago)
    created_at_str = created_dt.isoformat()
    
    # 75% for Warung Kosan (_WK_ID), 25% for Kantin Pagi (_KP_ID)
    mch_id = _WK_ID if _rng.random() < 0.75 else _KP_ID
    
    # 3 major transaction types
    txn_type = _rng.choice(["qris", "link", "cpm"])
    
    # Realistic status distribution
    r_val = _rng.random()
    if r_val < 0.80:
        status = "paid"
    elif r_val < 0.90:
        status = "pending"
    elif r_val < 0.95:
        status = "expired"
    else:
        status = _rng.choice(["cancelled", "failed", "refunded"])
        
    # Realistic amount distributions
    if txn_type == "link":
        amount = _rng.choice([150000, 200000, 350000, 500000, 850000, 1200000])
    else:
        amount = _rng.choice([10000, 15000, 25000, 35000, 50000, 75000, 100000])
        
    # Transaction attributes
    if txn_type == "qris":
        title = "QRIS payment"
        cpm = None
        if status == "paid":
            payer = Payer(
                masked_phone=f"+62 812 •••• {_rng.randint(1000, 9999)}",
                issuer_name=_rng.choice(_issuers)
            )
        else:
            payer = None
        invoice_number = None
        link_url = None
        customer = None
        note = _rng.choice(_notes) if _rng.random() < 0.4 else None
    elif txn_type == "cpm":
        title = "QRIS · CPM"
        payer = None
        if status == "paid":
            cpm = Cpm(
                issuer_name=_rng.choice(_issuers),
                masked_account=f"•••• {_rng.randint(1000, 9999)}"
            )
        else:
            cpm = None
        invoice_number = None
        link_url = None
        customer = None
        note = None
    else:  # link
        title = _rng.choice(["Rent Payment", "Utilities Bill", "Special Order", "Catering Service"])
        payer = None
        cpm = None
        customer = _rng.choice(_customers)
        short_id = mch_id[-4:].upper()
        day_str = created_dt.strftime("%Y%m%d")
        invoice_number = f"INV-{short_id}-{day_str}-{i:04d}"
        slug = title.lower().replace(" ", "-")
        link_url = f"https://paprika.app/pay/{short_id.lower()}-{slug}-{i:04d}"
        note = None

    # Reference format: PPK-[A-Z0-9]{4}-[A-Z0-9]{4}
    ref_part1 = "".join(_rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=4))
    ref_part2 = "".join(_rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=4))
    ref = f"PPK-{ref_part1}-{ref_part2}"
    
    # Timestamps
    if status == "paid":
        paid_dt = created_dt + timedelta(minutes=_rng.randint(1, 10))
        paid_at = paid_dt.isoformat()
        expires_at = (created_dt + timedelta(minutes=15)).isoformat() if txn_type == "qris" else None
    else:
        paid_at = None
        expires_at = (created_dt + timedelta(minutes=15)).isoformat() if txn_type == "qris" else (created_dt + timedelta(hours=24)).isoformat()

    type_code = txn_type.upper()
    status_code = status[:4].upper()
    txn_id = f"txn_01HX5{type_code}{status_code}{i:06d}"
    
    dummy_txn = Transaction(
        id=txn_id,
        merchant_id=mch_id,
        type=txn_type,
        title=title,
        ref=ref,
        amount=amount,
        status=status,
        customer=customer,
        note=note,
        invoice_number=invoice_number,
        link_url=link_url,
        payer=payer,
        cpm=cpm,
        created_at=created_at_str,
        paid_at=paid_at,
        expires_at=expires_at
    )
    SEED_TRANSACTIONS.append(dummy_txn)

# Mutable in-memory transaction store — keyed by transaction id.
TRANSACTIONS: dict[str, Transaction] = {t.id: t for t in SEED_TRANSACTIONS}

# Counter per merchant per day for invoice-number generation.
# Key: (merchant_id, "YYYYMMDD") → next counter value.
INVOICE_COUNTERS: dict[tuple[str, str], int] = {}

# Track used invoice numbers per merchant to detect collisions.
# Key: (merchant_id, invoice_number) → True
INVOICE_TAKEN: dict[tuple[str, str], bool] = {}

# Populate INVOICE_TAKEN with the generated seed transactions
for t in SEED_TRANSACTIONS:
    if t.invoice_number:
        INVOICE_TAKEN[(t.merchant_id, t.invoice_number)] = True

