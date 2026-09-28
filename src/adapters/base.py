from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from src.models.device import Device
from src.models.actions import ActionResult, ScreenshotResult

class DeviceAdapter(ABC):
    @abstractmethod
    def get_device_info(self) -> Device:
        """Return metadata, status, and capabilities of the device."""
        pass

    @abstractmethod
    def screenshot(self, scale: float = 1.0, format: str = "jpeg") -> ScreenshotResult:
        """Capture the screen of the device."""
        pass

    @abstractmethod
    def click(self, x: int, y: int, button: str = "left", click_count: int = 1, return_screenshot: bool = False) -> ActionResult:
        """Click at (x, y) on the device."""
        pass
        
    @abstractmethod
    def type_text(self, text: str, return_screenshot: bool = False) -> ActionResult:
        """Type Unicode text onto the device."""
        pass

    @abstractmethod
    def press_key(self, key: str, modifiers: List[str] = [], return_screenshot: bool = False) -> ActionResult:
        """Press a keyboard key with optional modifiers."""
        pass

    @abstractmethod
    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int, return_screenshot: bool = False) -> ActionResult:
        """Click and drag from (from_x, from_y) to (to_x, to_y)."""
        pass

    @abstractmethod
    def scroll(self, x: int, y: int, delta_x: int = 0, delta_y: int = -50, return_screenshot: bool = False) -> ActionResult:
        """Scroll at (x, y) with the specified pixel deltas."""
        pass

    @abstractmethod
    def get_ui_tree(self, max_depth: int = 8, max_children: int = 25) -> Dict[str, Any]:
        """Read the visible accessibility/UI element tree."""
        pass

    @abstractmethod
    def open_app(self, name: str) -> Dict[str, Any]:
        """Launch or activate an application by name."""
        pass

    @abstractmethod
    def get_active_app(self) -> Dict[str, Any]:
        """Get details of the currently active/frontmost application."""
        pass

    @abstractmethod
    def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in the device's default browser."""
        pass
