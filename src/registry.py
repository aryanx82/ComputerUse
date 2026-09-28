"""
Device Registry — dynamically discovers and manages connected platforms (macOS & Android).
"""

import subprocess
import shutil
from typing import Dict, List, Optional
from src.models.device import Device
from src.adapters.base import DeviceAdapter
from src.adapters.macos_adapter import MacOSAdapter
from src.adapters.android_adapter import AndroidAdapter


class DeviceRegistry:
    def __init__(self):
        self._adapters: Dict[str, DeviceAdapter] = {}
        self.discover_devices()

    def discover_devices(self):
        """
        Discover all local and connected hardware devices.
        1. Always registers the local macOS primary host.
        2. Detects any attached Android devices via ADB.
        """
        self._adapters.clear()

        # 1. macOS Primary Display
        mac_adapter = MacOSAdapter("mac-primary")
        self._adapters["mac-primary"] = mac_adapter

        # 2. Discover Android Devices via ADB
        self._discover_android_devices()

    def _discover_android_devices(self):
        """Query ADB for connected physical devices or emulators."""
        if not shutil.which("adb"):
            return

        try:
            proc = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=8.0)
            if proc.returncode != 0:
                return

            lines = proc.stdout.strip().splitlines()
            android_devices = []

            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                serial = parts[0]
                state = parts[1]

                metadata = {}
                for item in parts[2:]:
                    if ":" in item:
                        k, v = item.split(":", 1)
                        metadata[k] = v

                android_devices.append({
                    "serial": serial,
                    "state": state,
                    "model": metadata.get("model", ""),
                    "product": metadata.get("product", "")
                })

            for idx, dev in enumerate(android_devices):
                serial = dev["serial"]
                model_raw = dev["model"]

                # Generate friendly name
                friendly_name = f"Android Device ({serial})"
                if "X710" in model_raw or "gts9" in dev["product"]:
                    friendly_name = f"Samsung Galaxy Tab S9 ({serial})"
                elif model_raw:
                    friendly_name = f"Android {model_raw} ({serial})"

                # Primary device identifier based on serial
                dev_id = f"android-{serial.lower()}"
                adapter = AndroidAdapter(device_id=dev_id, serial=serial, model_name=friendly_name)
                self._adapters[dev_id] = adapter

                # If this is the first connected Android device, also create an alias "android-primary"
                if idx == 0:
                    self._adapters["android-primary"] = adapter

        except Exception:
            # ADB offline or query failed; fail gracefully
            pass

    def refresh(self):
        """Re-scan for newly attached or detached devices."""
        self.discover_devices()

    def get_adapter(self, device_id: str) -> DeviceAdapter:
        if device_id not in self._adapters:
            # Try refreshing in case a device was just connected
            self.refresh()
            if device_id not in self._adapters:
                available = list(self._adapters.keys())
                raise ValueError(f"Device '{device_id}' not found. Available devices: {available}")
        return self._adapters[device_id]

    def list_devices(self) -> List[Device]:
        """Return a unique list of all connected devices (deduplicating aliases)."""
        seen_serials = set()
        devices = []
        for dev_id, adapter in self._adapters.items():
            info = adapter.get_device_info()
            # De-duplicate aliases that point to the same hardware
            identifier = f"{info.platform}:{info.id}"
            if identifier in seen_serials:
                continue
            seen_serials.add(identifier)
            devices.append(info)
        return devices
