"""Interactive dev-trigger CLI for the Paprika backend simulator.

Reads `dev_tools/config.json` for base_url and merchant_id, then shows a menu:

    1) Trigger a payment        (asks for amount)
    2) Expire a pending txn     (asks for transaction id)
    3) Fail a pending txn       (asks for transaction id + optional reason)
    4) Toggle merchant scan_cpm capability
    5) Force-logout the device
    6) Generate a scannable QR image  (CPM customer QR or custom payload)

Trigger options 1-5 are stdlib-only. Option 6 needs the `qrcode` package
(in requirements.txt). Run from the simulator root or from inside dev_tools/.

    python dev_tools/trigger.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

# Force UTF-8 on Windows so em-dashes/arrows in prompts don't blow up cp1252.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except AttributeError:
        pass


CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        sys.exit(f"Config file missing: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def post(base_url: str, path: str, body: dict[str, Any]) -> tuple[int, Any]:
    url = base_url.rstrip("/") + path
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach {url}: {e.reason}")


def prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{label}{suffix}: ").strip()
    return raw if raw else (default or "")


def prompt_amount() -> int:
    while True:
        raw = prompt("Amount (IDR)", "50000")
        try:
            value = int(raw)
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("  Please enter a positive integer.")


def show_response(status: int, body: Any) -> None:
    print(f"\n  → HTTP {status}")
    if isinstance(body, (dict, list)):
        print("  " + json.dumps(body, indent=2).replace("\n", "\n  "))
    elif body is not None:
        print(f"  {body}")
    print()


MENU = """
Paprika simulator — dev triggers
================================
  1) Trigger payment           (creates pending QRIS, settles via WS after delay)
  2) Expire pending txn        (asks for transaction id)
  3) Fail pending txn          (asks for transaction id + optional reason)
  4) Toggle merchant scan_cpm
  5) Force-logout device
  6) Generate QR image         (scannable PNG for the merchant app)
  q) Quit
"""

# CPM issuer presets — matches the simulator's _parse_qris_issuer support set.
_ISSUERS = ["BCA", "Mandiri", "BRI", "BNI", "GoPay", "OVO", "Dana", "ShopeePay"]
_ISSUER_PREFIX = {
    "BCA": "ID.CO.BCA.WWW",
    "Mandiri": "ID.CO.MANDIRI.WWW",
    "BRI": "ID.CO.BRI.WWW",
    "BNI": "ID.CO.BNI.WWW",
    "GoPay": "ID.CO.GOPAY.WWW",
    "OVO": "ID.CO.OVO.WWW",
    "Dana": "ID.CO.DANA.WWW",
    "ShopeePay": "ID.CO.SHOPEEPAY.WWW",
}

# Onboarding fixtures — MUST match `backend_simulator/fixtures/company.py`
# and `fixtures/merchants.py`. Updating those files? Update this list too.
_COMPANY = {
    "name": "Kos Pak Harso",
    "code": "A4F28K19PQ7M3XR9LB42",
    "uri": "paprika://company/A4F28K19PQ7M3XR9LB42",
}
_MERCHANT_FIXTURES = [
    # (label, code, claim_status_on_first_claim)
    ("Warung Kosan",  "WK4F82D19PQ7M3XR9LB4",  "already linked, 200"),
    ("Kantin Pagi",   "KP7M3F4P2KJ7DZQ9WK4F8", "already linked, 200"),
    ("Gerobak Rica",  "GR4P2KJ7DZQ9WK4F8M3F4", "already linked, 200"),
    ("Kopi Tenda",    "KT9X2JZQ9PKM3F4R7HD8",  "UNCLAIMED, 201 Created"),
]


def _faux_cpm_payload(issuer: str) -> str:
    """Plausible CPM-style QRIS payload — contains the issuer name so the
    simulator's `_parse_qris_issuer` recognises it. Not EMVCO/CRC valid."""
    prefix = _ISSUER_PREFIX[issuer]
    account = uuid.uuid4().hex[:16].upper()
    return (
        f"00020101021126620010{prefix}0118{account}"
        f"5204481253033605802ID5913CUSTOMER PAYER6013JAKARTA SELATAN6304ABCD"
    )


def _open_in_default_viewer(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as e:
        print(f"  Could not open viewer: {e}")


def action_payment(cfg: dict[str, Any]) -> None:
    amount = prompt_amount()
    status, body = post(
        cfg["base_url"],
        "/v1/_dev/trigger-payment",
        {"merchant_id": cfg["merchant_id"], "amount": amount},
    )
    show_response(status, body)


def action_expire(cfg: dict[str, Any]) -> None:
    txn_id = prompt("Transaction id (txn_...)")
    if not txn_id:
        print("  No id supplied — cancelled.\n")
        return
    status, body = post(
        cfg["base_url"],
        "/v1/_dev/trigger-expire",
        {"transaction_id": txn_id},
    )
    show_response(status, body)


def action_fail(cfg: dict[str, Any]) -> None:
    txn_id = prompt("Transaction id (txn_...)")
    if not txn_id:
        print("  No id supplied — cancelled.\n")
        return
    reason = prompt("Reason (blank = none)")
    payload: dict[str, Any] = {"transaction_id": txn_id}
    if reason:
        payload["reason"] = reason
    status, body = post(cfg["base_url"], "/v1/_dev/trigger-fail", payload)
    show_response(status, body)


def action_merchant_update(cfg: dict[str, Any]) -> None:
    toggle = prompt("Toggle scan_cpm? (y/N)", "n").lower() == "y"
    status, body = post(
        cfg["base_url"],
        "/v1/_dev/trigger-merchant-update",
        {"merchant_id": cfg["merchant_id"], "toggle_scan_cpm": toggle},
    )
    show_response(status, body)


def action_logout(cfg: dict[str, Any]) -> None:
    reason = prompt("Reason", "remote_revoke")
    status, body = post(
        cfg["base_url"],
        "/v1/_dev/trigger-logout",
        {"reason": reason} if reason else {},
    )
    show_response(status, body)


def action_qr_image(cfg: dict[str, Any]) -> None:
    try:
        import qrcode  # noqa: F401  (imported here so options 1-5 don't need it)
    except ImportError:
        print(
            "  The 'qrcode' package is not installed.\n"
            "  Run: pip install -r requirements.txt\n"
        )
        return

    print("\n  QR mode:")
    print("    a) CPM customer QR        (for the merchant app's Scan-QRIS flow)")
    print("    b) Company onboarding QR  (for the app's session-claim flow)")
    print("    c) Merchant claim QR      (for the app's add-merchant flow)")
    print("    d) Custom payload         (raw text)")
    mode = prompt("Choose", "a").lower()

    if mode == "a":
        print()
        for i, iss in enumerate(_ISSUERS, 1):
            print(f"    {i}) {iss}")
        try:
            idx = int(prompt("Issuer", "1")) - 1
            issuer = _ISSUERS[idx]
        except (ValueError, IndexError):
            print("  Invalid issuer choice.\n")
            return
        payload = _faux_cpm_payload(issuer)
        label = f"cpm_{issuer.lower()}"

    elif mode == "b":
        payload = _COMPANY["uri"]
        label = "company_kos_pak_harso"
        print(f"\n  Company: {_COMPANY['name']}  (code {_COMPANY['code']})")

    elif mode == "c":
        print()
        for i, (name, code, status) in enumerate(_MERCHANT_FIXTURES, 1):
            print(f"    {i}) {name:<14} {code}   [{status}]")
        try:
            idx = int(prompt("Merchant", str(len(_MERCHANT_FIXTURES)))) - 1
            name, code, _status = _MERCHANT_FIXTURES[idx]
        except (ValueError, IndexError):
            print("  Invalid merchant choice.\n")
            return
        payload = f"paprika://merchant/{code}"
        label = f"merchant_{name.lower().replace(' ', '_')}"

    elif mode == "d":
        payload = prompt("Payload")
        if not payload:
            print("  Empty payload — cancelled.\n")
            return
        label = "custom"

    else:
        print(f"  Unknown mode: {mode!r}\n")
        return

    import qrcode

    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{label}_{uuid.uuid4().hex[:6]}.png"

    qr = qrcode.QRCode(border=2, box_size=10)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(out_path))

    preview = payload if len(payload) <= 80 else payload[:80] + "..."
    print(f"\n  Saved:   {out_path}")
    print(f"  Payload: {preview}")

    if prompt("Open the image now?", "y").lower() == "y":
        _open_in_default_viewer(out_path)
    print()


ACTIONS = {
    "1": action_payment,
    "2": action_expire,
    "3": action_fail,
    "4": action_merchant_update,
    "5": action_logout,
    "6": action_qr_image,
}


def main() -> None:
    cfg = load_config()
    print(f"Target: {cfg['base_url']}    merchant_id: {cfg['merchant_id']}")
    while True:
        print(MENU)
        choice = input("Select: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            return
        action = ACTIONS.get(choice)
        if action is None:
            print(f"  Unknown choice: {choice!r}\n")
            continue
        try:
            action(cfg)
        except KeyboardInterrupt:
            print("\n  Cancelled.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
