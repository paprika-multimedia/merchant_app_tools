"""Interactive dev-trigger CLI for the Paprika backend simulator.

Reads `dev_tools/config.json` for base_url and merchant_id, then shows a menu:

    1) Trigger a payment        (asks for amount)
    2) Expire a pending txn     (asks for transaction id)
    3) Fail a pending txn       (asks for transaction id + optional reason)
    4) Toggle merchant scan_cpm capability
    5) Force-logout the device

No external deps — uses urllib from the stdlib. Run from the simulator root or
from inside dev_tools/.

    python dev_tools/trigger.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


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
  q) Quit
"""


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


ACTIONS = {
    "1": action_payment,
    "2": action_expire,
    "3": action_fail,
    "4": action_merchant_update,
    "5": action_logout,
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
