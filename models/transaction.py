from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Payer(BaseModel):
    """Payer block for type=qris paid transactions — Spec.md §2.3."""

    model_config = ConfigDict(populate_by_name=True)

    masked_phone: str | None = Field(alias="masked_phone", default=None)
    issuer_name: str | None = Field(alias="issuer_name", default=None)


class Cpm(BaseModel):
    """CPM block — payer_name intentionally omitted on mobile sessions — Spec.md §2.3."""

    model_config = ConfigDict(populate_by_name=True)

    issuer_name: str = Field(alias="issuer_name")
    masked_account: str = Field(alias="masked_account")
    # payer_name is NEVER included in mobile-facing responses per Spec §2.3 hard rule.


# class Transaction(BaseModel):
#     """Transaction resource — Spec.md §2.3."""

#     model_config = ConfigDict(populate_by_name=True)

#     id: str
#     merchant_id: str = Field(alias="merchant_id")
#     type: Literal["qris", "link", "cpm"]
#     title: str
#     ref: str
#     amount: int
#     status: Literal["pending", "paid", "expired", "cancelled", "failed", "refunded"]
#     customer: str | None = None
#     note: str | None = None
#     invoice_number: str | None = Field(alias="invoice_number", default=None)
#     link_url: str | None = Field(alias="link_url", default=None)
#     payer: Payer | None = None
#     cpm: Cpm | None = None
#     created_at: str = Field(alias="created_at")
#     paid_at: str | None = Field(alias="paid_at", default=None)
#     expires_at: str | None = Field(alias="expires_at", default=None)


class Transaction(BaseModel):
    """Transaction resource — Spec.md §2.3."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    merchant_id: str = Field(alias="merchant_id")
    type: Literal["qris", "link", "cpm"]
    title: str
    ref: str
    amount: int
    status: Literal["pending", "paid", "expired", "cancelled", "failed", "refunded"]

    qr_payload: str | None = Field(alias="qr_payload", default=None)

    customer: str | None = None
    note: str | None = None
    invoice_number: str | None = Field(alias="invoice_number", default=None)
    link_url: str | None = Field(alias="link_url", default=None)
    payer: Payer | None = None
    cpm: Cpm | None = None
    created_at: str = Field(alias="created_at")
    paid_at: str | None = Field(alias="paid_at", default=None)
    expires_at: str | None = Field(alias="expires_at", default=None)
