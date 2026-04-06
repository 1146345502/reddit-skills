"""Reddit Extension Bridge Server

Extension connects here (WebSocket), CLI commands come through the same port (role=cli),
Bridge routes commands to Extension and returns results to CLI.

Usage:
    python scripts/bridge_server.py

Port: 9334 (override with --port)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from typing import Any

import websockets
from websockets.server import ServerConnection

logger = logging.getLogger("reddit-bridge")


class BridgeServer:
    def __init__(self) -> None:
        self._extension_ws: ServerConnection | None = None
        self._pending: dict[str, asyncio.Future[Any]] = {}

    async def handle(self, ws: ServerConnection) -> None:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
        except (TimeoutError, Exception) as e:
            logger.warning("Handshake timeout or failure: %s", e)
            return

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        role = msg.get("role")
        if role == "extension":
            await self._handle_extension(ws)
        elif role == "cli":
            await self._handle_cli(ws, msg)
        else:
            logger.warning("Unknown role: %s", role)

    async def _handle_extension(self, ws: ServerConnection) -> None:
        logger.info("Extension connected")
        self._extension_ws = ws
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                msg_id = msg.get("id")
                if msg_id and msg_id in self._pending:
                    future = self._pending.pop(msg_id)
                    if not future.done():
                        future.set_result(msg)
        finally:
            self._extension_ws = None
            logger.info("Extension disconnected")
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(ConnectionError("Extension disconnected"))
            self._pending.clear()

    async def _handle_cli(self, ws: ServerConnection, msg: dict) -> None:
        if msg.get("method") == "ping_server":
            await ws.send(
                json.dumps({"result": {"extension_connected": self._extension_ws is not None}})
            )
            return

        if not self._extension_ws:
            err = (
                "Extension not connected. Please ensure Chrome has "
                "the Reddit Bridge extension installed and enabled."
            )
            await ws.send(json.dumps({"error": err}))
            return

        msg_id = str(uuid.uuid4())
        msg["id"] = msg_id

        loop = asyncio.get_event_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending[msg_id] = future

        await self._extension_ws.send(json.dumps(msg))

        try:
            result = await asyncio.wait_for(future, timeout=90.0)
            await ws.send(json.dumps(result))
        except TimeoutError:
            self._pending.pop(msg_id, None)
            await ws.send(json.dumps({"error": "Command execution timeout (90s)"}))
        except ConnectionError as e:
            await ws.send(json.dumps({"error": str(e)}))


async def main(port: int) -> None:
    server = BridgeServer()
    async with websockets.serve(server.handle, "localhost", port):
        logger.info("Bridge server started: ws://localhost:%d", port)
        logger.info("Waiting for browser extension to connect...")
        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Reddit Extension Bridge Server")
    parser.add_argument("--port", type=int, default=9334, help="Listen port (default: 9334)")
    args = parser.parse_args()

    asyncio.run(main(args.port))
