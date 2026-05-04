from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Inner error object per Spec.md §11."""

    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(alias="error")
    message: str
    details: dict[str, Any] | None = None

    def to_wire(self) -> dict[str, Any]:
        """Return the wire-format dict (Spec §11 envelope)."""
        out: dict[str, Any] = {"error": self.code, "message": self.message}
        if self.details:
            out["details"] = self.details
        return out


# Localized message tables.  Keys are error codes; values are (id, en) tuples.
MESSAGES: dict[str, tuple[str, str]] = {
    "not_found": ("Sumber daya tidak ditemukan", "Resource not found"),
    "unauthenticated": ("Token tidak valid atau sudah kedaluwarsa", "Token is invalid or expired"),
    "forbidden": ("Akses ditolak", "Access denied"),
    "capability_disabled": (
        "Fitur ini tidak diaktifkan untuk merchant ini",
        "This capability is not enabled for this merchant",
    ),
    "idempotency_required": (
        "Header Idempotency-Key wajib ada untuk endpoint ini",
        "Idempotency-Key header is required for this endpoint",
    ),
    "idempotency_mismatch": (
        "Kunci idempotency sudah digunakan dengan body berbeda",
        "Idempotency key was already used with a different request body",
    ),
    "invalid_request": ("Permintaan tidak valid", "Invalid request"),
    "validation_error": ("Data tidak valid", "Validation error"),
    "name_mismatch": (
        "Nama tidak cocok. Ketik nama merchant dengan tepat.",
        "Name does not match. Type the merchant name exactly.",
    ),
    "claimed_elsewhere": (
        "Kode ini sudah diklaim oleh perusahaan lain",
        "This code is already claimed by another company",
    ),
    "invoice_taken": (
        "Nomor invoice sudah digunakan",
        "Invoice number is already in use",
    ),
    "already_settled": (
        "Transaksi sudah selesai dan tidak dapat dibatalkan",
        "Transaction is already settled and cannot be cancelled",
    ),
    "invalid_code": (
        "Kode tidak valid. Kode harus 20 karakter alfanumerik.",
        "Invalid code. Code must be 20 alphanumeric characters.",
    ),
    "invalid_qr": (
        "QR tidak dapat dibaca sebagai QRIS",
        "QR could not be parsed as QRIS",
    ),
    "wrong_mode": (
        "QR ini adalah MPM, bukan CPM. Minta pelanggan menampilkan QR dari aplikasinya.",
        "This QR is MPM, not CPM. Ask the customer to show their QR from their app.",
    ),
    "issuer_unsupported": (
        "Bank atau dompet ini belum didukung",
        "This bank or wallet is not yet supported",
    ),
    "amount_too_low": (
        "Jumlah minimum adalah Rp 1.000",
        "Minimum amount is IDR 1,000",
    ),
    "amount_too_high": (
        "Jumlah melebihi batas maksimum untuk merchant ini",
        "Amount exceeds the ceiling for this merchant",
    ),
    "rate_limited": (
        "Terlalu banyak permintaan. Coba lagi nanti.",
        "Too many requests. Please try again later.",
    ),
    "server_error": (
        "Terjadi kesalahan pada server. Silakan coba lagi.",
        "An unexpected server error occurred. Please try again.",
    ),
    "refresh_revoked": (
        "Sesi sudah tidak valid. Silakan masuk kembali.",
        "Session is no longer valid. Please sign in again.",
    ),
}


def localized_message(code: str, locale: str) -> str:
    """Return the localized human-readable message for an error code."""
    pair = MESSAGES.get(code, ("Terjadi kesalahan", "An error occurred"))
    return pair[1] if locale == "en" else pair[0]


def make_error(code: str, locale: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the Spec §11 error envelope dict."""
    out: dict[str, Any] = {"error": code, "message": localized_message(code, locale)}
    if details:
        out["details"] = details
    return out
