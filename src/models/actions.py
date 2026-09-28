from dataclasses import dataclass
from typing import Optional

@dataclass
class ScreenshotResult:
    image_base64: str
    width: int
    height: int

@dataclass
class ActionResult:
    success: bool
    error: Optional[str] = None
    screenshot: Optional[ScreenshotResult] = None
