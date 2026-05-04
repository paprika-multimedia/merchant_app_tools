from pydantic import BaseModel, ConfigDict, Field


class DeviceInfo(BaseModel):
    """Device registration block inside session claim."""

    model_config = ConfigDict(populate_by_name=True)

    platform: str
    model: str
    push_token: str | None = Field(alias="push_token", default=None)


class SessionClaimRequest(BaseModel):
    """Body for POST /sessions/claim — Spec §3.1."""

    model_config = ConfigDict(populate_by_name=True)

    company_code: str = Field(alias="company_code")
    device: DeviceInfo


class SessionRefreshRequest(BaseModel):
    """Body for POST /sessions/refresh — Spec §3.1.1."""

    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(alias="refresh_token")


class MerchantClaimRequest(BaseModel):
    """Body for POST /merchants/claim — Spec §4.2.1."""

    model_config = ConfigDict(populate_by_name=True)

    merchant_code: str = Field(alias="merchant_code")


class MerchantDeleteRequest(BaseModel):
    """Body for DELETE /merchants/:id — Spec §4.2.2."""

    model_config = ConfigDict(populate_by_name=True)

    confirm_name: str = Field(alias="confirm_name")


class QrisCreateRequest(BaseModel):
    """Body for POST /merchants/:id/qris — Spec §4.4."""

    model_config = ConfigDict(populate_by_name=True)

    amount: int
    note: str | None = Field(default=None, max_length=80)


class LinkCreateRequest(BaseModel):
    """Body for POST /merchants/:id/links — Spec §4.5."""

    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(max_length=40)
    amount: int
    customer: str | None = None
    invoice_number: str | None = Field(alias="invoice_number", default=None)


class ScanRequest(BaseModel):
    """Body for POST /merchants/:id/scan — Spec §4.6."""

    model_config = ConfigDict(populate_by_name=True)

    qr_payload: str = Field(alias="qr_payload")
    amount: int


class PushRegisterRequest(BaseModel):
    """Body for POST /devices/me/push — Spec §4.7."""

    model_config = ConfigDict(populate_by_name=True)

    push_token: str = Field(alias="push_token")
