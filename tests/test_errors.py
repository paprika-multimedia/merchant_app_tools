"""Unit tests for error localization — Spec §11 + §1.3."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.errors import localized_message, make_error


def test_known_code_returns_indonesian_by_default():
    msg = localized_message("not_found", "id")
    assert "tidak" in msg.lower() or "ditemukan" in msg.lower()


def test_known_code_returns_english_when_en():
    msg = localized_message("not_found", "en")
    assert "not found" in msg.lower()


def test_unknown_code_returns_fallback():
    msg = localized_message("totally_unknown_code", "en")
    assert isinstance(msg, str)
    assert len(msg) > 0


def test_make_error_envelope_shape():
    envelope = make_error("unauthenticated", "en")
    assert envelope["error"] == "unauthenticated"
    assert "message" in envelope
    assert isinstance(envelope["message"], str)


def test_make_error_with_details():
    envelope = make_error("capability_disabled", "en", details={"capability": "scan_cpm"})
    assert envelope["details"]["capability"] == "scan_cpm"


def test_idempotency_required_localized_id():
    msg = localized_message("idempotency_required", "id")
    assert "idempotency" in msg.lower() or "wajib" in msg.lower()


def test_idempotency_required_localized_en():
    msg = localized_message("idempotency_required", "en")
    assert "idempotency" in msg.lower() and "required" in msg.lower()
