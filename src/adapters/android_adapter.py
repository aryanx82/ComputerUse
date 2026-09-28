"""
Android Adapter — controls Android tablets and phones via ADB (Android Debug Bridge).

Provides full observation and interaction:
- Screen capture: Direct PNG streaming via `adb exec-out screencap -p`
- Input injection: Taps, swipes, drags, keyevents via `adb shell input`
- Accessibility tree: UI hierarchy parsing via `adb shell uiautomator dump`
- App management: Launching and active package inspection via `dumpsys` and `monkey`
"""

import subprocess
import io
import time
import base64
import re
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
from PIL import Image

from src.adapters.base import DeviceAdapter
from src.models.device import Device, DeviceCapabilities, DeviceStatus
from src.models.actions import ActionResult, ScreenshotResult


# Standard keycode mapping for Android KeyEvent
ANDROID_KEYCODES: Dict[str, int] = {
    # System Controls
    "home": 3,
    "back": 4,
    "recents": 187,
    "app_switch": 187,
    "power": 26,
    "volume_up": 24,
    "volume_down": 25,
    "mute": 164,
    "wakeup": 224,
    "sleep": 223,
    "menu": 82,
    "search": 84,
    "camera": 27,
    
    # Text and Navigation
    "enter": 66,
    "return": 66,
    "tab": 61,
    "space": 62,
    "delete": 67,
    "backspace": 67,
    "escape": 111,
    "esc": 111,
    "up": 19,
    "arrow_up": 19,
    "down": 20,
    "arrow_down": 20,
    "left": 21,
    "arrow_left": 21,
    "right": 22,
    "arrow_right": 22,
    "page_up": 92,
    "page_down": 93,
    "move_home": 122,
    "move_end": 123,
    "paste": 279,
    "copy": 278,
    "cut": 277,
}

# Common application package aliases for Android
COMMON_APP_PACKAGES: Dict[str, str] = {
    "settings": "com.android.settings",
    "chrome": "com.android.chrome",
    "browser": "com.android.chrome",
    "camera": "com.sec.android.app.camera",
    "calculator": "com.sec.android.app.popupcalculator",
    "files": "com.sec.android.app.myfiles",
    "youtube": "com.google.android.youtube",
    "clock": "com.sec.android.app.clockpackage",
    "maps": "com.google.android.apps.maps",
    "contacts": "com.samsung.android.app.contacts",
    "messages": "com.samsung.android.messaging",
    "gallery": "com.sec.android.gallery3d",
    "playstore": "com.android.vending",
}


class AndroidAdapter(DeviceAdapter):
    """Adapter that controls an Android device via ADB."""

    def __init__(self, device_id: str, serial: str, model_name: str = ""):
        self.device_id = device_id
        self.serial = serial
        self._cached_model = model_name
        self._screen_width = 0
        self._screen_height = 0

    def _run_adb(self, args: List[str], timeout: float = 10.0, check: bool = True) -> subprocess.CompletedProcess:
        """Run an ADB command targeting this device."""
        cmd = ["adb", "-s", self.serial] + args
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ADB command failed: {' '.join(cmd)}\nStderr: {e.stderr.strip()}")
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"ADB command timed out after {timeout}s: {' '.join(cmd)}")

    def _run_adb_binary(self, args: List[str], timeout: float = 10.0) -> bytes:
        """Run an ADB command and capture binary output directly."""
        cmd = ["adb", "-s", self.serial] + args
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=timeout)
            if res.returncode != 0:
                raise RuntimeError(f"ADB binary command failed: {res.stderr.decode('utf-8', errors='ignore')}")
            return res.stdout
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"ADB binary command timed out after {timeout}s: {' '.join(cmd)}")

    def _check_connection(self) -> bool:
        """Check if device is currently online and authorized."""
        try:
            res = self._run_adb(["get-state"], timeout=3.0, check=False)
            return res.returncode == 0 and "device" in res.stdout.strip()
        except Exception:
            return False

    # ── Device Info ──────────────────────────────────────────────────

    def get_device_info(self) -> Device:
        is_connected = self._check_connection()
        error_msg = None if is_connected else "Device offline or unauthorized"

        # Fetch device model and brand if connected
        name = self._cached_model or f"Android Device ({self.serial})"
        if is_connected:
            try:
                brand = self._run_adb(["shell", "getprop", "ro.product.brand"], timeout=2.0).stdout.strip().capitalize()
                model = self._run_adb(["shell", "getprop", "ro.product.model"], timeout=2.0).stdout.strip()
                if brand and model:
                    name = f"{brand} {model} ({self.serial})"
            except Exception:
                pass

        return Device(
            id=self.device_id,
            name=name,
            platform="android",
            capabilities=DeviceCapabilities(
                screenshot=True,
                click=True,
                type_text=True,
                press_key=True,
                drag=True,
                scroll=True,
                ui_tree=True,
                open_app=True,
            ),
            status=DeviceStatus(
                is_connected=is_connected,
                error=error_msg,
            ),
        )

    # ── Screenshot ──────────────────────────────────────────────────

    def screenshot(self, scale: float = 1.0, format: str = "jpeg") -> ScreenshotResult:
        """
        Capture the screen via direct PNG stream from SurfaceFlinger.
        Downscales and converts to JPEG for token efficiency.
        """
        png_bytes = self._run_adb_binary(["exec-out", "screencap", "-p"], timeout=8.0)
        if not png_bytes or len(png_bytes) < 100:
            raise RuntimeError("Received empty or corrupt screenshot from Android device")

        # Load image with PIL
        image = Image.open(io.BytesIO(png_bytes))
        self._screen_width, self._screen_height = image.width, image.height

        # Apply scale if requested
        if scale < 1.0:
            new_w = max(1, int(image.width * scale))
            new_h = max(1, int(image.height * scale))
            image = image.resize((new_w, new_h), Image.Resampling.BILINEAR)

        # Convert to RGB if saving as JPEG
        output_buffer = io.BytesIO()
        if format.lower() == "png":
            image.save(output_buffer, format="PNG")
        else:
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.save(output_buffer, format="JPEG", quality=80)

        data = output_buffer.getvalue()
        b64_str = base64.b64encode(data).decode("utf-8")

        return ScreenshotResult(
            image_base64=b64_str,
            width=image.width,
            height=image.height,
        )

    # ── Click / Tap ─────────────────────────────────────────────────

    def click(self, x: int, y: int, button: str = "left", click_count: int = 1, return_screenshot: bool = False) -> ActionResult:
        """
        Perform a touch tap at screen coordinates (x, y).
        """
        try:
            for i in range(click_count):
                self._run_adb(["shell", "input", "tap", str(x), str(y)], timeout=4.0)
                if i < click_count - 1:
                    time.sleep(0.1)

            shot = None
            if return_screenshot:
                time.sleep(0.2)
                shot = self.screenshot(scale=0.5)

            return ActionResult(success=True, screenshot=shot)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ── Typing ──────────────────────────────────────────────────────

    def type_text(self, text: str, return_screenshot: bool = False) -> ActionResult:
        """
        Type text on the Android device.
        Spaces are escaped as %s as required by ADB input text.
        Non-ASCII characters (e.g. emojis) are safely filtered because Android's
        KeyCharacterMap throws a NullPointerException on unmappable unicode glyphs.
        """
        if not text:
            return ActionResult(success=True)

        # Android input text only supports characters mapped by KeyCharacterMap (ASCII 32-126)
        filtered = "".join(c for c in text if 32 <= ord(c) <= 126)
        if not filtered:
            return ActionResult(success=True)

        try:
            # Escape spaces for ADB input text
            escaped = filtered.replace(" ", "%s")
            # Safely escape for POSIX sh on Android
            escaped_shell = "'" + escaped.replace("'", "'\\''") + "'"
            
            self._run_adb(["shell", f"input text {escaped_shell}"], timeout=6.0)

            shot = None
            if return_screenshot:
                time.sleep(0.2)
                shot = self.screenshot(scale=0.5)

            return ActionResult(success=True, screenshot=shot)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ── Key Press ───────────────────────────────────────────────────

    def press_key(self, key: str, modifiers: List[str] = [], return_screenshot: bool = False) -> ActionResult:
        """
        Press a physical or virtual button on the device (Home, Back, Recents, Power, Volume, etc.).
        """
        key_lower = key.strip().lower()
        keycode = ANDROID_KEYCODES.get(key_lower)

        # Support single letter keys (a-z: 29-54) and digits (0-9: 7-16)
        if keycode is None:
            if len(key_lower) == 1 and key_lower.isalpha():
                keycode = ord(key_lower) - ord('a') + 29
            elif len(key_lower) == 1 and key_lower.isdigit():
                keycode = int(key_lower) + 7
            else:
                return ActionResult(success=False, error=f"Unknown Android key: '{key}'")

        try:
            self._run_adb(["shell", "input", "keyevent", str(keycode)], timeout=4.0)

            shot = None
            if return_screenshot:
                time.sleep(0.2)
                shot = self.screenshot(scale=0.5)

            return ActionResult(success=True, screenshot=shot)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ── Drag & Swipe & Scroll ───────────────────────────────────────

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int, return_screenshot: bool = False) -> ActionResult:
        """
        Drag from (from_x, from_y) to (to_x, to_y) using an interpolated swipe gesture.
        """
        try:
            # 600ms duration produces a smooth drag action
            self._run_adb(["shell", "input", "swipe", str(from_x), str(from_y), str(to_x), str(to_y), "600"], timeout=5.0)

            shot = None
            if return_screenshot:
                time.sleep(0.2)
                shot = self.screenshot(scale=0.5)

            return ActionResult(success=True, screenshot=shot)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def scroll(self, x: int, y: int, delta_x: int = 0, delta_y: int = -50, return_screenshot: bool = False) -> ActionResult:
        """
        Scroll the screen. On touch screens, scrolling down means swiping upward.
        """
        try:
            # Default to screen center if x or y are 0
            if self._screen_width == 0:
                self._screen_width = 1600
                self._screen_height = 2560

            start_x = x if x > 0 else self._screen_width // 2
            start_y = y if y > 0 else self._screen_height // 2

            # Delta_y < 0 means scroll down (finger moves up)
            end_x = max(10, min(self._screen_width - 10, start_x + delta_x))
            end_y = max(10, min(self._screen_height - 10, start_y + delta_y))

            # 300ms swipe simulates natural flick/scroll
            self._run_adb(["shell", "input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), "300"], timeout=5.0)

            shot = None
            if return_screenshot:
                time.sleep(0.3)
                shot = self.screenshot(scale=0.5)

            return ActionResult(success=True, screenshot=shot)
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    # ── Accessibility UI Tree ───────────────────────────────────────

    def get_ui_tree(self, max_depth: int = 8, max_children: int = 25) -> Dict[str, Any]:
        """
        Dump and parse the device's accessibility hierarchy using uiautomator dump.
        Normalizes XML attributes into our unified schema.
        """
        dump_path = "/data/local/tmp/tool_window_dump.xml"
        try:
            self._run_adb(["shell", "uiautomator", "dump", dump_path], timeout=6.0)
            xml_content = self._run_adb(["shell", "cat", dump_path], timeout=5.0).stdout
        except Exception as e:
            raise RuntimeError(f"Failed to dump UI hierarchy: {e}")

        if not xml_content or "<hierarchy" not in xml_content:
            raise RuntimeError("Invalid or empty UI hierarchy dumped from device")

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise RuntimeError(f"XML parse error in UI hierarchy: {e}")

        # Active app information from dump root
        active_app = self.get_active_app()

        def parse_node(elem, depth: int) -> Dict[str, Any]:
            node_dict: Dict[str, Any] = {}

            # Clean role name (e.g. android.widget.Button -> Button)
            raw_class = elem.attrib.get("class", "")
            role = raw_class.split(".")[-1] if raw_class else "View"
            node_dict["role"] = role

            text = elem.attrib.get("text", "").strip()
            if text:
                node_dict["text"] = text

            desc = elem.attrib.get("content-desc", "").strip()
            if desc:
                node_dict["description"] = desc

            res_id = elem.attrib.get("resource-id", "").strip()
            if res_id:
                node_dict["resource_id"] = res_id

            # Parse bounds: "[x1,y1][x2,y2]"
            bounds_str = elem.attrib.get("bounds", "")
            match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
            if match:
                x1, y1, x2, y2 = map(int, match.groups())
                node_dict["bounds"] = {
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1
                }

            # Interactive states
            states = {}
            for state_key in ["clickable", "scrollable", "focusable", "focused", "checked", "enabled"]:
                if elem.attrib.get(state_key) == "true":
                    states[state_key] = True
            if states:
                node_dict["states"] = states

            # Children
            if depth < max_depth:
                children = []
                for child in list(elem)[:max_children]:
                    parsed_child = parse_node(child, depth + 1)
                    if parsed_child:
                        children.append(parsed_child)
                if children:
                    node_dict["children"] = children

            return node_dict

        tree_data = parse_node(root, 0)
        tree_data["app_name"] = active_app.get("package", "Android")
        tree_data["package"] = active_app.get("package", "")
        tree_data["activity"] = active_app.get("activity", "")
        return tree_data

    # ── App Management ──────────────────────────────────────────────

    def open_app(self, name: str) -> Dict[str, Any]:
        """
        Launch an application by friendly name or package identifier.
        """
        name_clean = name.strip().lower()
        package = COMMON_APP_PACKAGES.get(name_clean, name.strip())

        try:
            # Launch via monkey tool (handles finding the main launcher activity automatically)
            cmd = ["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]
            res = self._run_adb(cmd, timeout=5.0)

            time.sleep(0.3)
            active = self.get_active_app()
            return {
                "status": f"Launched '{name}'",
                "package": package,
                "current_focus": active.get("package", ""),
            }
        except Exception as e:
            raise RuntimeError(f"Failed to launch '{name}' on Android: {e}")

    def get_active_app(self) -> Dict[str, Any]:
        """
        Inspect current focus using dumpsys window.
        """
        try:
            output = self._run_adb(["shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], timeout=4.0).stdout
            # Example format: Window{1c2075b u0 net.fullstackhub.anydisplay/net.fullstackhub.anydisplay.DisplayActivity}
            match = re.search(r"([a-zA-Z0-9_\.]+)/([a-zA-Z0-9_\.]+)", output)
            if match:
                pkg, act = match.groups()
                return {"name": pkg, "package": pkg, "activity": act}
            return {"name": "Android System", "package": "com.android.system", "activity": ""}
        except Exception:
            return {"name": "Unknown", "package": "", "activity": ""}

    def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in default Android browser."""
        cmd = ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url]
        res = self._run_adb(cmd, timeout=5.0)
        return {"status": f"Opened URL '{url}'", "url": url}
