"""WebSocket listener for the Paprika backend simulator.

Connects to ws_url from `dev_tools/config.json`, sends the auth frame, then
prints every event as it arrives. Pair with `trigger.py` in another terminal
to see triggers fire end-to-end.

    python dev_tools/listen.py

Requires the `websockets` package (already in `requirements.txt`).
"""
from __future__ import annotations

import asyncio
import json
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import websockets
except ImportError:
    sys.exit(
        "The 'websockets' package is not installed. "
        "Run: pip install -r requirements.txt"
    )


CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        sys.exit(f"Config file missing: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


async def run(cfg: dict[str, Any]) -> None:
    url = cfg["ws_url"]
    token = cfg.get("session_token", "mock_session_token_30d")
    print(f"[{stamp()}] connecting to {url}")
    try:
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps({"type": "auth", "token": token}))
            ack_raw = await ws.recv()
            try:
                ack = json.loads(ack_raw)
            except Exception:
                ack = {"raw": ack_raw}
            print(f"[{stamp()}] auth ack: {ack}")
            print(f"[{stamp()}] listening (Ctrl+C to quit)")

            while True:
                raw = await ws.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    print(f"[{stamp()}] (non-JSON) {raw}")
                    continue

                kind = msg.get("event") or msg.get("type") or "?"
                if kind == "ping":
                    print(f"[{stamp()}] ping")
                    continue
                print(f"[{stamp()}] {kind}")
                print("  " + json.dumps(msg, indent=2).replace("\n", "\n  "))
    except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
        print(f"[{stamp()}] connection closed: {e}")


def main() -> None:
    cfg = load_config()

    if sys.platform != "win32":
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, loop.stop)

    try:
        asyncio.run(run(cfg))
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
