import subprocess
import time
from typing import List, Dict, Any, Optional
from src.registry import DeviceRegistry
from src.models.actions import ActionResult, ScreenshotResult
from src.utils.ui_tree import normalize_ui_tree, search_elements
from src.safety.guardrails import guardrails

class ToolRouter:
    def __init__(self, registry: DeviceRegistry):
        self.registry = registry

    def screenshot(self, device_id: str, scale: float = 1.0, format: str = "jpeg") -> ScreenshotResult:
        adapter = self.registry.get_adapter(device_id)
        return adapter.screenshot(scale, format)

    def click(self, device_id: str, x: int, y: int, button: str = "left", click_count: int = 1, return_screenshot: bool = False) -> ActionResult:
        params = {"x": x, "y": y, "button": button, "click_count": click_count}
        allowed, reason = guardrails.validate_action(device_id, "click", params)
        if not allowed:
            guardrails.log_audit_record(device_id, "click", params, False, error=reason)
            return ActionResult(success=False, error=reason)

        t0 = time.time()
        adapter = self.registry.get_adapter(device_id)
        res = adapter.click(x, y, button=button, click_count=click_count, return_screenshot=return_screenshot)
        guardrails.log_audit_record(device_id, "click", params, res.success, res.error, (time.time() - t0) * 1000)
        return res

    def drag(self, device_id: str, from_x: int, from_y: int, to_x: int, to_y: int, return_screenshot: bool = False) -> ActionResult:
        params = {"from_x": from_x, "from_y": from_y, "to_x": to_x, "to_y": to_y}
        allowed, reason = guardrails.validate_action(device_id, "drag", params)
        if not allowed:
            guardrails.log_audit_record(device_id, "drag", params, False, error=reason)
            return ActionResult(success=False, error=reason)

        t0 = time.time()
        adapter = self.registry.get_adapter(device_id)
        res = adapter.drag(from_x, from_y, to_x, to_y, return_screenshot=return_screenshot)
        guardrails.log_audit_record(device_id, "drag", params, res.success, res.error, (time.time() - t0) * 1000)
        return res

    def scroll(self, device_id: str, x: int, y: int, delta_x: int = 0, delta_y: int = -50, return_screenshot: bool = False) -> ActionResult:
        params = {"x": x, "y": y, "delta_x": delta_x, "delta_y": delta_y}
        allowed, reason = guardrails.validate_action(device_id, "scroll", params)
        if not allowed:
            guardrails.log_audit_record(device_id, "scroll", params, False, error=reason)
            return ActionResult(success=False, error=reason)

        t0 = time.time()
        adapter = self.registry.get_adapter(device_id)
        res = adapter.scroll(x, y, delta_x=delta_x, delta_y=delta_y, return_screenshot=return_screenshot)
        guardrails.log_audit_record(device_id, "scroll", params, res.success, res.error, (time.time() - t0) * 1000)
        return res

    def type_text(self, device_id: str, text: str, return_screenshot: bool = False) -> ActionResult:
        params = {"text": text}
        allowed, reason = guardrails.validate_action(device_id, "type_text", params)
        if not allowed:
            guardrails.log_audit_record(device_id, "type_text", params, False, error=reason)
            return ActionResult(success=False, error=reason)

        t0 = time.time()
        adapter = self.registry.get_adapter(device_id)
        res = adapter.type_text(text, return_screenshot=return_screenshot)
        guardrails.log_audit_record(device_id, "type_text", params, res.success, res.error, (time.time() - t0) * 1000)
        return res

    def press_key(self, device_id: str, key: str, modifiers: List[str] = [], return_screenshot: bool = False) -> ActionResult:
        params = {"key": key, "modifiers": modifiers}
        allowed, reason = guardrails.validate_action(device_id, "press_key", params)
        if not allowed:
            guardrails.log_audit_record(device_id, "press_key", params, False, error=reason)
            return ActionResult(success=False, error=reason)

        t0 = time.time()
        adapter = self.registry.get_adapter(device_id)
        res = adapter.press_key(key, modifiers=modifiers, return_screenshot=return_screenshot)
        guardrails.log_audit_record(device_id, "press_key", params, res.success, res.error, (time.time() - t0) * 1000)
        return res

    def get_ui_tree(self, device_id: str, max_depth: int = 8, max_children: int = 25, normalize: bool = True) -> Dict[str, Any]:
        adapter = self.registry.get_adapter(device_id)
        raw_tree = adapter.get_ui_tree(max_depth=max_depth, max_children=max_children)
        if normalize:
            platform = adapter.get_device_info().platform
            return normalize_ui_tree(raw_tree, platform)
        return raw_tree

    def find_ui_elements(
        self,
        device_id: str,
        text_query: Optional[str] = None,
        role_query: Optional[str] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        tree = self.get_ui_tree(device_id, normalize=True)
        return search_elements(tree, text_query=text_query, role_query=role_query, max_results=max_results)

    def click_ui_element(
        self,
        device_id: str,
        text_query: str,
        role_query: Optional[str] = None
    ) -> ActionResult:
        matches = self.find_ui_elements(device_id, text_query=text_query, role_query=role_query, max_results=5)
        if not matches:
            return ActionResult(
                success=False,
                error=f"No UI element found matching query '{text_query}' (role: {role_query}) on {device_id}"
            )

        target = matches[0]
        center = target.get("center")
        if not center or "x" not in center or "y" not in center:
            return ActionResult(
                success=False,
                error=f"Element matched ('{target.get('label')}') but has no clickable center coordinates."
            )

        x, y = center["x"], center["y"]
        return self.click(device_id, x, y)

    def open_app(self, device_id: str, name: str) -> Dict[str, Any]:
        params = {"name": name}
        allowed, reason = guardrails.validate_action(device_id, "open_app", params, active_app=name)
        if not allowed:
            guardrails.log_audit_record(device_id, "open_app", params, False, error=reason)
            raise PermissionError(reason)

        t0 = time.time()
        adapter = self.registry.get_adapter(device_id)
        res = adapter.open_app(name)
        guardrails.log_audit_record(device_id, "open_app", params, True, duration_ms=(time.time() - t0) * 1000)
        return res

    def get_active_app(self, device_id: str) -> Dict[str, Any]:
        adapter = self.registry.get_adapter(device_id)
        return adapter.get_active_app()

    def open_url(self, device_id: str, url: str) -> Dict[str, Any]:
        params = {"url": url}
        allowed, reason = guardrails.validate_action(device_id, "open_url", params)
        if not allowed:
            guardrails.log_audit_record(device_id, "open_url", params, False, error=reason)
            raise PermissionError(reason)

        t0 = time.time()
        adapter = self.registry.get_adapter(device_id)
        res = adapter.open_url(url)
        guardrails.log_audit_record(device_id, "open_url", params, True, duration_ms=(time.time() - t0) * 1000)
        return res

    def get_clipboard(self, device_id: str = "mac-primary") -> str:
        if "mac" in device_id:
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3.0)
            return res.stdout
        return "Clipboard inspection only currently supported on macOS host"

    def set_clipboard(self, device_id: str, text: str) -> ActionResult:
        if "mac" in device_id:
            try:
                subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True, timeout=3.0)
                return ActionResult(success=True)
            except Exception as e:
                return ActionResult(success=False, error=str(e))
        return ActionResult(success=False, error="Clipboard set not supported on this platform")
