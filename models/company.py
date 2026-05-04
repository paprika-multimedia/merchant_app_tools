from pydantic import BaseModel, ConfigDict, Field


class Company(BaseModel):
    """Company resource — Spec.md §2.1."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    code: str
    qr_payload: str = Field(alias="qr_payload")
    timezone: str
    created_at: str = Field(alias="created_at")
