from dataclasses import dataclass

@dataclass
class DeviceCapabilities:
    screenshot: bool
    click: bool
    type_text: bool
    press_key: bool = True
    drag: bool = True
    scroll: bool = True
    ui_tree: bool = True
    open_app: bool = True

@dataclass
class DeviceStatus:
    is_connected: bool
    error: str | None = None

@dataclass
class Device:
    id: str
    name: str
    platform: str
    capabilities: DeviceCapabilities
    status: DeviceStatus
