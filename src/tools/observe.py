import base64
import json
from typing import Dict, Any, List
try:
    from mcp.server.mcpserver import Image
except (ImportError, ModuleNotFoundError):
    from mcp.server.fastmcp import Image
from src.router import ToolRouter
from src.registry import DeviceRegistry

def register_observe_tools(mcp, router: ToolRouter, registry: DeviceRegistry):
    
    @mcp.tool()
    def list_devices() -> List[Dict[str, Any]]:
        """
        List all connected and available devices that can be controlled.
        Returns device ID, friendly name, platform, and online status.
        """
        devices = registry.list_devices()
        return [
            {
                "id": d.id,
                "name": d.name,
                "platform": d.platform,
                "is_connected": d.status.is_connected,
                "capabilities": {
                    "screenshot": d.capabilities.screenshot,
                    "click": d.capabilities.click,
                    "type_text": d.capabilities.type_text,
                    "press_key": d.capabilities.press_key,
                    "drag": d.capabilities.drag,
                    "scroll": d.capabilities.scroll,
                    "ui_tree": d.capabilities.ui_tree,
                    "open_app": d.capabilities.open_app,
                }
            }
            for d in devices
        ]

    @mcp.tool()
    def get_device_info(device_id: str = "mac-primary") -> Dict[str, Any]:
        """
        Get detailed capability and connection status for a specific device.
        """
        adapter = registry.get_adapter(device_id)
        device = adapter.get_device_info()
        return {
            "id": device.id,
            "name": device.name,
            "platform": device.platform,
            "capabilities": {
                "screenshot": device.capabilities.screenshot,
                "click": device.capabilities.click,
                "type_text": device.capabilities.type_text,
                "press_key": device.capabilities.press_key,
                "drag": device.capabilities.drag,
                "scroll": device.capabilities.scroll,
                "ui_tree": device.capabilities.ui_tree,
                "open_app": device.capabilities.open_app,
            },
            "status": {
                "is_connected": device.status.is_connected,
                "error": device.status.error
            }
        }

    @mcp.tool()
    def screenshot(device_id: str = "mac-primary", scale: float = 1.0) -> Image:
        """
        Capture the current screen of the specified device.
        Returns the image as an MCP ImageContent block.

        Args:
            device_id: Target device ID (default "mac-primary").
            scale: Downscale factor from 0.1 to 1.0 (default 1.0 = native resolution).
                   Use 0.5 to reduce token usage during rapid exploration.

        Coordinate System Note:
            Origin (0,0) is always the top-left of the screen in native pixels.
        """
        result = router.screenshot(device_id, scale=scale)
        image_bytes = base64.b64decode(result.image_base64)
        return Image(data=image_bytes, format="jpeg")

    @mcp.tool()
    def get_ui_tree(device_id: str = "mac-primary", max_depth: int = 6) -> str:
        """
        Get the accessibility UI element tree of the currently active window/screen.
        Returns a structured JSON tree containing roles, labels/titles, bounds, and states.

        Use this to inspect buttons, input fields, menus, and labels without relying solely
        on visual OCR. Highly token-efficient for discovering interactive coordinates.
        """
        tree = router.get_ui_tree(device_id, max_depth=max_depth)
        return json.dumps(tree, indent=2)

    @mcp.tool()
    def get_active_app(device_id: str = "mac-primary") -> Dict[str, Any]:
        """
        Get the currently active/frontmost application name, bundle ID, and PID.
        """
        return router.get_active_app(device_id)

    @mcp.tool()
    def find_ui_elements(
        device_id: str = "mac-primary",
        text_query: str = "",
        role_query: str = "",
        max_results: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Search the UI element tree on any device for elements matching text or role.
        Returns a list of matching UI elements with their label, role, bounding box,
        and pre-calculated center click coordinates (x, y).

        Use this to discover where buttons, links, or fields are located on screen!
        """
        tq = text_query.strip() if text_query else None
        rq = role_query.strip() if role_query else None
        return router.find_ui_elements(device_id, text_query=tq, role_query=rq, max_results=max_results)
