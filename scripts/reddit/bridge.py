"""BridgePage - Page-compatible API via browser extension bridge.

CLI commands are sent via WebSocket to bridge_server.py,
which forwards them to the browser extension for execution.

Each call is a short-lived connection (send one command, receive one reply).
"""

from __future__ import annotations

import json
import os
from typing import Any

import websockets.sync.client as ws_client

from .errors import BridgeError, ElementNotFoundError

BRIDGE_URL = "ws://localhost:9334"


class BridgePage:
    """Extension Bridge implementation compatible with CDP Page interface."""

    def __init__(self, bridge_url: str = BRIDGE_URL) -> None:
        self._bridge_url = bridge_url

    # ─── Internal communication ─────────────────────────────────

    def _call(self, method: str, params: dict | None = None) -> Any:
        """Send one command to bridge server and wait for result."""
        msg: dict[str, Any] = {"role": "cli", "method": method}
        if params:
            msg["params"] = params
        try:
            with ws_client.connect(self._bridge_url, max_size=50 * 1024 * 1024, proxy=None) as wsc:
                wsc.send(json.dumps(msg, ensure_ascii=False))
                raw = wsc.recv(timeout=90)
        except OSError as e:
            raise BridgeError(f"Cannot connect to bridge server ({self._bridge_url}): {e}") from e

        resp = json.loads(raw)
        if resp.get("error"):
            raise BridgeError(f"Bridge error: {resp['error']}")
        return resp.get("result")

    # ─── Navigation ─────────────────────────────────────────────

    def navigate(self, url: str) -> None:
        self._call("navigate", {"url": url})

    def wait_for_load(self, timeout: float = 60.0) -> None:
        self._call("wait_for_load", {"timeout": int(timeout * 1000)})

    def wait_dom_stable(self, timeout: float = 10.0, interval: float = 0.5) -> None:
        self._call(
            "wait_dom_stable",
            {
                "timeout": int(timeout * 1000),
                "interval": int(interval * 1000),
            },
        )

    # ─── JavaScript execution ───────────────────────────────────

    def evaluate(self, expression: str, timeout: float = 30.0) -> Any:
        return self._call("evaluate", {"expression": expression})

    # ─── Element queries ────────────────────────────────────────

    def query_selector(self, selector: str) -> str | None:
        found = self._call("has_element", {"selector": selector})
        return "found" if found else None

    def query_selector_all(self, selector: str) -> list[str]:
        count = self.get_elements_count(selector)
        return ["found"] * count

    def has_element(self, selector: str) -> bool:
        return bool(self._call("has_element", {"selector": selector}))

    def wait_for_element(self, selector: str, timeout: float = 30.0) -> str:
        found = self._call(
            "wait_for_selector",
            {
                "selector": selector,
                "timeout": int(timeout * 1000),
            },
        )
        if not found:
            raise ElementNotFoundError(selector)
        return "found"

    # ─── Element operations ─────────────────────────────────────

    def click_element(self, selector: str) -> None:
        self._call("click_element", {"selector": selector})

    def input_text(self, selector: str, text: str) -> None:
        self._call("input_text", {"selector": selector, "text": text})

    def input_content_editable(self, selector: str, text: str) -> None:
        self._call("input_content_editable", {"selector": selector, "text": text})

    def get_element_text(self, selector: str) -> str | None:
        return self._call("get_element_text", {"selector": selector})

    def get_element_attribute(self, selector: str, attr: str) -> str | None:
        return self._call("get_element_attribute", {"selector": selector, "attr": attr})

    def get_elements_count(self, selector: str) -> int:
        result = self._call("get_elements_count", {"selector": selector})
        return int(result) if result is not None else 0

    def remove_element(self, selector: str) -> None:
        self._call("remove_element", {"selector": selector})

    def hover_element(self, selector: str) -> None:
        self._call("hover_element", {"selector": selector})

    def select_all_text(self, selector: str) -> None:
        self._call("select_all_text", {"selector": selector})

    # ─── Scrolling ──────────────────────────────────────────────

    def scroll_by(self, x: int, y: int) -> None:
        self._call("scroll_by", {"x": x, "y": y})

    def scroll_to(self, x: int, y: int) -> None:
        self._call("scroll_to", {"x": x, "y": y})

    def scroll_to_bottom(self) -> None:
        self._call("scroll_to_bottom")

    def scroll_element_into_view(self, selector: str) -> None:
        self._call("scroll_element_into_view", {"selector": selector})

    def scroll_nth_element_into_view(self, selector: str, index: int) -> None:
        self._call("scroll_nth_element_into_view", {"selector": selector, "index": index})

    def get_scroll_top(self) -> int:
        result = self._call("get_scroll_top")
        return int(result) if result is not None else 0

    def get_viewport_height(self) -> int:
        result = self._call("get_viewport_height")
        return int(result) if result is not None else 768

    # ─── Input events ───────────────────────────────────────────

    def press_key(self, key: str) -> None:
        self._call("press_key", {"key": key})

    def type_text(self, text: str, delay_ms: int = 50) -> None:
        self._call("type_text", {"text": text, "delayMs": delay_ms})

    def mouse_move(self, x: float, y: float) -> None:
        self._call("mouse_move", {"x": x, "y": y})

    def mouse_click(self, x: float, y: float, button: str = "left") -> None:
        self._call("mouse_click", {"x": x, "y": y, "button": button})

    def dispatch_wheel_event(self, delta_y: float) -> None:
        self._call("dispatch_wheel_event", {"deltaY": delta_y})

    # ─── File upload ────────────────────────────────────────────

    def set_file_input(self, selector: str, files: list[str]) -> None:
        """Upload local files via chrome.debugger + DOM.setFileInputFiles."""
        abs_paths = [os.path.abspath(path) for path in files]
        self._call("set_file_input", {"selector": selector, "files": abs_paths})

    # ─── Compatibility helpers ──────────────────────────────────

    def is_server_running(self) -> bool:
        """Check if bridge server is running."""
        try:
            with ws_client.connect(self._bridge_url, open_timeout=3, proxy=None) as wsc:
                wsc.send(json.dumps({"role": "cli", "method": "ping_server"}))
                raw = wsc.recv(timeout=5)
            resp = json.loads(raw)
            return "result" in resp
        except Exception:
            return False

    def is_extension_connected(self) -> bool:
        """Check if browser extension is connected to bridge server."""
        try:
            with ws_client.connect(self._bridge_url, open_timeout=3, proxy=None) as wsc:
                wsc.send(json.dumps({"role": "cli", "method": "ping_server"}))
                raw = wsc.recv(timeout=5)
            resp = json.loads(raw)
            return bool(resp.get("result", {}).get("extension_connected"))
        except Exception:
            return False
