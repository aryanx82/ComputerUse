"""
macOS Adapter — communicates with the Swift native daemon over a Unix Domain Socket.

The daemon handles ScreenCaptureKit (screenshots), CGEvent (mouse/keyboard/drag/scroll),
and AXUIElement (accessibility tree) operations. This adapter sends JSON commands
and receives JSON responses.
"""

import socket
import json
import os
import uuid
import time
import shutil
import subprocess
from typing import Optional, List, Dict, Any
from src.adapters.base import DeviceAdapter
from src.models.device import Device, DeviceCapabilities, DeviceStatus
from src.models.actions import ActionResult, ScreenshotResult

DAEMON_SOCKET_PATH = os.path.expanduser("~/.computer-use-tool/daemon.sock")
SOCKET_TIMEOUT = 12.0


class MacOSAdapter(DeviceAdapter):
    """Adapter that controls macOS via the native Swift daemon."""

    def __init__(self, device_id: str = "mac-primary"):
        self.device_id = device_id
        self._sock: Optional[socket.socket] = None

    @staticmethod
    def _find_daemon_binary() -> Optional[str]:
        """Locate the compiled Swift daemon executable."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidates = [
            os.path.join(base_dir, "native", ".build", "release", "computer-use-daemon"),
            os.path.join(base_dir, "native", ".build", "debug", "computer-use-daemon"),
            shutil.which("computer-use-daemon"),
        ]
        for p in candidates:
            if p and os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return None

    def _ensure_daemon_running(self):
        """Check if the Swift daemon is responsive; if not, automatically launch it."""
        if os.path.exists(DAEMON_SOCKET_PATH):
            try:
                test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                test_sock.settimeout(1.0)
                test_sock.connect(DAEMON_SOCKET_PATH)
                test_sock.close()
                return  # Socket is live and responsive
            except Exception:
                # Stale socket from dead process
                try:
                    os.unlink(DAEMON_SOCKET_PATH)
                except Exception:
                    pass

        daemon_bin = self._find_daemon_binary()
        if not daemon_bin:
            return  # No binary found, let connection error report it

        os.makedirs(os.path.dirname(DAEMON_SOCKET_PATH), exist_ok=True)
        log_path = os.path.expanduser("~/.computer-use-tool/daemon.log")
        log_file = open(log_path, "a")

        try:
            subprocess.Popen(
                [daemon_bin],
                stdout=log_file,
                stderr=log_file,
                start_new_session=True,
            )
        except Exception:
            return

        # Wait up to 3 seconds for the socket to initialize
        for _ in range(30):
            time.sleep(0.1)
            if os.path.exists(DAEMON_SOCKET_PATH):
                try:
                    test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    test_sock.settimeout(1.0)
                    test_sock.connect(DAEMON_SOCKET_PATH)
                    test_sock.close()
                    return
                except Exception:
                    continue

    def _get_socket(self) -> socket.socket:
        if self._sock is not None:
            return self._sock

        self._ensure_daemon_running()

        if not os.path.exists(DAEMON_SOCKET_PATH):
            raise ConnectionError(
                f"macOS daemon socket not found at {DAEMON_SOCKET_PATH}.\n"
                "Make sure the Swift daemon is built and running:\n"
                "  ./run.sh --status"
            )
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(SOCKET_TIMEOUT)
        s.connect(DAEMON_SOCKET_PATH)
        self._sock = s
        return self._sock

    def _close_socket(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _send_command(self, action: str, params: Optional[dict] = None) -> dict:
        """
        Send a JSON command to the Swift daemon over a persistent Unix Domain Socket.
        Reuses the existing connection and auto-reconnects on disconnection.
        """
        if params is None:
            params = {}

        request = {
            "id": str(uuid.uuid4()),
            "action": action,
            "params": params,
        }
        message = json.dumps(request).encode("utf-8") + b"\n"

        for attempt in range(2):
            try:
                sock = self._get_socket()
                sock.sendall(message)

                response_chunks: List[bytes] = []
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        raise ConnectionError("Connection closed unexpectedly by daemon.")
                    response_chunks.append(chunk)
                    if chunk.endswith(b"\n") or b"\n" in chunk:
                        break

                raw_response = b"".join(response_chunks).decode("utf-8").strip()
                return json.loads(raw_response)

            except (BrokenPipeError, ConnectionResetError, ConnectionError) as e:
                self._close_socket()
                if attempt == 0:
                    continue  # Retry once on reconnect
                raise ConnectionError(f"Daemon socket communication error: {e}")
            except socket.timeout:
                self._close_socket()
                raise ConnectionError(
                    f"Daemon did not respond within {SOCKET_TIMEOUT}s. "
                    "It may be busy, permission prompt pending, or unresponsive."
                )
            except json.JSONDecodeError as e:
                self._close_socket()
                raise ConnectionError(f"Invalid JSON response from daemon: {e}")
            except Exception as e:
                self._close_socket()
                raise ConnectionError(f"Communication error: {e}")

    def _parse_action_result(self, resp: dict) -> ActionResult:
        """Helper to convert daemon response into an ActionResult with optional screenshot."""
        if not resp.get("success"):
            return ActionResult(success=False, error=resp.get("error", "Unknown error"))

        data = resp.get("data") or {}
        screenshot = None
        if "screenshot" in data and isinstance(data["screenshot"], dict):
            sdata = data["screenshot"]
            screenshot = ScreenshotResult(
                image_base64=sdata.get("base64", ""),
                width=sdata.get("width", 0),
                height=sdata.get("height", 0)
            )

        return ActionResult(success=True, screenshot=screenshot)

    # ── Device Info ──────────────────────────────────────────────────

    def get_device_info(self) -> Device:
        is_connected = os.path.exists(DAEMON_SOCKET_PATH)
        return Device(
            id=self.device_id,
            name="macOS Primary Display",
            platform="macos",
            capabilities=DeviceCapabilities(
                screenshot=True,
                click=True,
                type_text=True,
                press_key=True,
                drag=True,
                scroll=True,
                ui_tree=True,
                open_app=True
            ),
            status=DeviceStatus(
                is_connected=is_connected,
                error=None if is_connected else "Daemon not running",
            ),
        )

    # ── Screenshot ──────────────────────────────────────────────────

    def screenshot(self, scale: float = 1.0, format: str = "jpeg") -> ScreenshotResult:
        resp = self._send_command("screenshot", {
            "scale": scale,
            "quality": 0.8,
        })
        if not resp.get("success"):
            raise RuntimeError(resp.get("error", "Unknown error during screenshot"))

        data = resp.get("data", {})
        return ScreenshotResult(
            image_base64=data.get("base64", ""),
            width=data.get("width", 0),
            height=data.get("height", 0),
        )

    # ── Mouse Click & Drag & Scroll ─────────────────────────────────

    def click(self, x: int, y: int, button: str = "left", click_count: int = 1, return_screenshot: bool = False) -> ActionResult:
        try:
            resp = self._send_command("mouseClick", {
                "x": x,
                "y": y,
                "button": button,
                "clickCount": click_count,
                "returnScreenshot": return_screenshot,
            })
            return self._parse_action_result(resp)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int, return_screenshot: bool = False) -> ActionResult:
        try:
            resp = self._send_command("mouseDrag", {
                "fromX": from_x,
                "fromY": from_y,
                "toX": to_x,
                "toY": to_y,
                "button": "left",
                "returnScreenshot": return_screenshot,
            })
            return self._parse_action_result(resp)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def scroll(self, x: int, y: int, delta_x: int = 0, delta_y: int = -50, return_screenshot: bool = False) -> ActionResult:
        try:
            resp = self._send_command("scroll", {
                "x": x,
                "y": y,
                "deltaX": delta_x,
                "deltaY": delta_y,
                "returnScreenshot": return_screenshot,
            })
            return self._parse_action_result(resp)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ── Keyboard & Typing ───────────────────────────────────────────

    def type_text(self, text: str, return_screenshot: bool = False) -> ActionResult:
        try:
            resp = self._send_command("typeText", {
                "text": text,
                "returnScreenshot": return_screenshot,
            })
            return self._parse_action_result(resp)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def press_key(self, key: str, modifiers: List[str] = [], return_screenshot: bool = False) -> ActionResult:
        try:
            resp = self._send_command("pressKey", {
                "key": key,
                "modifiers": modifiers,
                "returnScreenshot": return_screenshot,
            })
            return self._parse_action_result(resp)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ── Accessibility UI Tree ───────────────────────────────────────

    def get_ui_tree(self, max_depth: int = 8, max_children: int = 25) -> Dict[str, Any]:
        resp = self._send_command("getUITree", {
            "maxDepth": max_depth,
            "maxChildren": max_children,
        })
        if not resp.get("success"):
            raise RuntimeError(resp.get("error", "Unknown error inspecting UI tree"))
        return resp.get("data", {})

    # ── App Management ──────────────────────────────────────────────

    def open_app(self, name: str) -> Dict[str, Any]:
        resp = self._send_command("openApp", {"name": name})
        if not resp.get("success"):
            raise RuntimeError(resp.get("error", f"Failed to open app '{name}'"))
        return resp.get("data", {})

    def get_active_app(self) -> Dict[str, Any]:
        resp = self._send_command("getActiveApp", {})
        if not resp.get("success"):
            raise RuntimeError(resp.get("error", "Failed to get active application"))
        return resp.get("data", {})

    def open_url(self, url: str) -> Dict[str, Any]:
        import subprocess
        proc = subprocess.run(["/usr/bin/open", url], capture_output=True, text=True, timeout=5.0)
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to open URL '{url}': {proc.stderr.strip()}")
        return {"status": f"Opened URL '{url}'", "url": url}
