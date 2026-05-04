"""Unit tests confirming model wire shapes match Spec §2 exactly."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.company import Company
from models.merchant import Capabilities, Merchant
from models.transaction import Cpm, Payer, Transaction


def test_company_wire_shape():
    c = Company(
        id="cmp_01",
        name="Test Co",
        code="A4F28K19PQ7M3XR9LB42",
        qr_payload="paprika://company/A4F28K19PQ7M3XR9LB42",
        timezone="Asia/Jakarta",
        created_at="2024-01-01T00:00:00+07:00",
    )
    wire = c.model_dump(by_alias=True)
    assert "qr_payload" in wire
    assert "created_at" in wire
    assert wire["code"] == "A4F28K19PQ7M3XR9LB42"


def test_merchant_wire_shape():
    m = Merchant(
        id="mch_01",
        company_id="cmp_01",
        name="Warung",
        code="WK4F82D19PQ7M3XR9LB4",
        qr_payload="paprika://merchant/WK4F82D19PQ7M3XR9LB4",
        capabilities=Capabilities(scan_cpm=True, cpm_ceiling=2000000),
        today_total=1000,
        today_count=5,
        month_total=50000,
        unread_count=1,
        created_at="2024-01-01T00:00:00+07:00",
    )
    wire = m.model_dump(by_alias=True)
    assert "company_id" in wire
    assert "today_total" in wire
    assert "today_count" in wire
    assert "month_total" in wire
    assert "unread_count" in wire
    assert "capabilities" in wire
    assert wire["capabilities"]["scan_cpm"] is True
    assert wire["capabilities"]["cpm_ceiling"] == 2000000


def test_transaction_cpm_no_payer_name():
    """payer_name must NEVER appear in the Transaction or Cpm wire output — Spec §2.3."""
    txn = Transaction(
        id="txn_01",
        merchant_id="mch_01",
        type="cpm",
        title="QRIS · CPM",
        ref="PPK-AAAA-BBBB",
        amount=50000,
        status="paid",
        cpm=Cpm(issuer_name="BCA", masked_account="•••• 4021"),
        created_at="2025-01-01T00:00:00+07:00",
    )
    wire = txn.model_dump(by_alias=True, exclude_none=True)
    assert "payer_name" not in str(wire)
    assert "payer_name" not in wire.get("cpm", {})


def test_transaction_link_has_invoice_and_link_url():
    txn = Transaction(
        id="txn_02",
        merchant_id="mch_01",
        type="link",
        title="May rent",
        ref="PPK-CCCC-DDDD",
        amount=850000,
        status="pending",
        invoice_number="INV-WK-20250512-0001",
        link_url="https://paprika.app/pay/test",
        created_at="2025-01-01T00:00:00+07:00",
    )
    wire = txn.model_dump(by_alias=True, exclude_none=True)
    assert wire["invoice_number"] == "INV-WK-20250512-0001"
    assert wire["link_url"] == "https://paprika.app/pay/test"


def test_merchant_last_transaction_fields_present_when_set():
    """last_transaction_amount and last_transaction_at appear in wire output when set."""
    m = Merchant(
        id="mch_02",
        company_id="cmp_01",
        name="Warung",
        code="WK4F82D19PQ7M3XR9LB4",
        qr_payload="paprika://merchant/WK4F82D19PQ7M3XR9LB4",
        capabilities=Capabilities(scan_cpm=True, cpm_ceiling=2000000),
        today_total=50000,
        today_count=1,
        month_total=50000,
        unread_count=0,
        last_transaction_amount=5000,
        last_transaction_at="2026-05-04T07:37:00Z",
        created_at="2024-01-01T00:00:00+07:00",
    )
    wire = m.model_dump(by_alias=True)
    assert wire["last_transaction_amount"] == 5000
    assert wire["last_transaction_at"] == "2026-05-04T07:37:00Z"


def test_merchant_last_transaction_fields_null_when_never_paid():
    """Both fields must be None (and omitted under exclude_none) for never-paid merchants."""
    m = Merchant(
        id="mch_03",
        company_id="cmp_01",
        name="Gerobak Rica",
        code="GR4P2KJ7DZQ9WK4F8M3F4",
        qr_payload="paprika://merchant/GR4P2KJ7DZQ9WK4F8M3F4",
        capabilities=Capabilities(scan_cpm=False, cpm_ceiling=None),
        today_total=0,
        today_count=0,
        month_total=0,
        unread_count=0,
        created_at="2024-01-01T00:00:00+07:00",
    )
    wire_full = m.model_dump(by_alias=True)
    wire_exclude_none = m.model_dump(by_alias=True, exclude_none=True)
    assert wire_full["last_transaction_amount"] is None
    assert wire_full["last_transaction_at"] is None
    assert "last_transaction_amount" not in wire_exclude_none
    assert "last_transaction_at" not in wire_exclude_none


def test_merchant_fixture_last_tx_amounts():
    """Seeded fixtures carry deterministic last_transaction_amount values."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from fixtures.merchants import MERCHANT_WARUNG_KOSAN, MERCHANT_KANTIN_PAGI, MERCHANT_GEROBAK_RICA

    assert MERCHANT_WARUNG_KOSAN.last_transaction_amount == 5000
    assert MERCHANT_WARUNG_KOSAN.last_transaction_at is not None

    assert MERCHANT_KANTIN_PAGI.last_transaction_amount == 10000
    assert MERCHANT_KANTIN_PAGI.last_transaction_at is not None

    # Gerobak Rica has never received a payment.
    assert MERCHANT_GEROBAK_RICA.last_transaction_amount is None
    assert MERCHANT_GEROBAK_RICA.last_transaction_at is None


def test_transaction_qris_has_payer_block():
    txn = Transaction(
        id="txn_03",
        merchant_id="mch_01",
        type="qris",
        title="QRIS payment",
        ref="PPK-EEEE-FFFF",
        amount=25000,
        status="paid",
        payer=Payer(masked_phone="+62 812 •••• 1148", issuer_name="BCA Mobile"),
        created_at="2025-01-01T00:00:00+07:00",
        paid_at="2025-01-01T00:01:00+07:00",
    )
    wire = txn.model_dump(by_alias=True, exclude_none=True)
    assert "payer" in wire
    assert wire["payer"]["masked_phone"] == "+62 812 •••• 1148"
    assert wire["payer"]["issuer_name"] == "BCA Mobile"
