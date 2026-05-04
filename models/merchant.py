from pydantic import BaseModel, ConfigDict, Field


class Capabilities(BaseModel):
    """Merchant capability flags — Spec.md §2.2."""

    model_config = ConfigDict(populate_by_name=True)

    scan_cpm: bool = Field(alias="scan_cpm")
    cpm_ceiling: int | None = Field(alias="cpm_ceiling", default=None)


class Merchant(BaseModel):
    """Merchant resource — Spec.md §2.2."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    company_id: str | None = Field(alias="company_id", default=None)
    name: str
    code: str
    qr_payload: str = Field(alias="qr_payload")
    capabilities: Capabilities
    today_total: int = Field(alias="today_total")
    today_count: int = Field(alias="today_count")
    month_total: int = Field(alias="month_total")
    unread_count: int = Field(alias="unread_count")
    last_transaction_amount: int | None = Field(alias="last_transaction_amount", default=None)
    last_transaction_at: str | None = Field(alias="last_transaction_at", default=None)
    created_at: str = Field(alias="created_at")
