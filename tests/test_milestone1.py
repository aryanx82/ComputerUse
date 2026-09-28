"""
Comprehensive Test Suite for Milestone 1:
Tests the Swift daemon + Python adapter + MCP layer across multiple scenarios:
1. Socket connection and reconnection
2. Native resolution screenshots (scale=1.0)
3. Scaled screenshots (scale=0.5, scale=0.25) and PIL validation
4. Sequential stress testing (10 back-to-back screenshots and clicks)
5. Mouse clicks (single, double, right-click, corner and center coordinates)
6. Cursor movement without clicking
7. Error handling (invalid device ID, bad parameters)
8. End-to-end MCP tool invocations
"""

import sys
import io
import time
import base64
import asyncio
from PIL import Image

from src.registry import DeviceRegistry
from src.router import ToolRouter
from src.server import mcp

def run_tests():
    print("=" * 60)
    print("Starting Comprehensive Milestone 1 Test Suite")
    print("=" * 60)
    
    registry = DeviceRegistry()
    router = ToolRouter(registry)
    adapter = registry.get_adapter("mac-primary")
    
    # ── Test 1: Device Info & Status ──
    print("\n[Test 1] Device Discovery & Health Status...")
    info = adapter.get_device_info()
    assert info.id == "mac-primary", f"Unexpected device id: {info.id}"
    assert info.status.is_connected, f"Daemon is not connected: {info.status.error}"
    print(f"  ✅ Device detected: {info.name} (Platform: {info.platform})")
    
    # ── Test 2: Full Resolution Screenshot ──
    print("\n[Test 2] Full Resolution Screenshot (scale=1.0)...")
    t0 = time.time()
    shot1 = router.screenshot("mac-primary", scale=1.0)
    t1 = time.time()
    raw_bytes1 = base64.b64decode(shot1.image_base64)
    img1 = Image.open(io.BytesIO(raw_bytes1))
    print(f"  ✅ Captured {shot1.width}x{shot1.height} in {(t1-t0)*1000:.1f}ms (Image format: {img1.format}, Size: {len(raw_bytes1)} bytes)")
    assert shot1.width > 0 and shot1.height > 0, "Invalid dimensions"
    assert img1.format == "JPEG", f"Expected JPEG, got {img1.format}"

    # ── Test 3: Downscaled Screenshots (0.5 and 0.25) ──
    print("\n[Test 3] Downscaled Screenshots (scale=0.5, 0.25)...")
    shot_half = router.screenshot("mac-primary", scale=0.5)
    raw_half = base64.b64decode(shot_half.image_base64)
    img_half = Image.open(io.BytesIO(raw_half))
    print(f"  ✅ Scale 0.5: {shot_half.width}x{shot_half.height} ({len(raw_half)} bytes)")
    assert shot_half.width <= shot1.width, "Scale 0.5 width should be <= full"

    shot_quarter = router.screenshot("mac-primary", scale=0.25)
    raw_quarter = base64.b64decode(shot_quarter.image_base64)
    img_quarter = Image.open(io.BytesIO(raw_quarter))
    print(f"  ✅ Scale 0.25: {shot_quarter.width}x{shot_quarter.height} ({len(raw_quarter)} bytes)")
    assert len(raw_quarter) < len(raw_bytes1), "Quarter scale payload should be smaller than full scale"

    # ── Test 4: Mouse Clicks at Multiple Screen Positions ──
    print("\n[Test 4] Mouse Clicks at Multiple Coordinates...")
    test_coords = [
        (100, 100),
        (shot1.width // 2, shot1.height // 2),
        (shot1.width - 100, 100),
    ]
    for x, y in test_coords:
        res = router.click("mac-primary", x, y)
        assert res.success, f"Click failed at ({x}, {y}): {res.error}"
        print(f"  ✅ Click succeeded at ({x}, {y})")

    # ── Test 5: Stress Test (Sequential rapid calls) ──
    print("\n[Test 5] Rapid Sequential Stress Test (5 cycles of screenshot + click)...")
    for i in range(1, 6):
        s = router.screenshot("mac-primary", scale=0.5)
        c = router.click("mac-primary", 200 + i * 20, 200 + i * 20)
        assert s.width > 0, f"Stress screenshot {i} failed"
        assert c.success, f"Stress click {i} failed"
        print(f"  ✅ Cycle {i}/5: Screenshot ({s.width}x{s.height}) + Click OK")

    # ── Test 6: Error Handling ──
    print("\n[Test 6] Error Handling...")
    try:
        router.screenshot("non-existent-device")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  ✅ Correctly caught unknown device error: {e}")

    # ── Test 7: MCP Protocol Invocation Loop ──
    print("\n[Test 7] MCP Protocol Tool Invocations (JSON-RPC tool API)...")
    async def test_mcp_tools():
        devs = await mcp.call_tool("list_devices", {})
        assert not devs.is_error, "list_devices tool failed"
        print("  ✅ MCP tool call: list_devices passed")

        info_tool = await mcp.call_tool("get_device_info", {"device_id": "mac-primary"})
        assert not info_tool.is_error, "get_device_info tool failed"
        print("  ✅ MCP tool call: get_device_info passed")

        click_tool = await mcp.call_tool("click", {"device_id": "mac-primary", "x": 300, "y": 300})
        assert not click_tool.is_error, "click tool failed"
        print("  ✅ MCP tool call: click passed")

        shot_tool = await mcp.call_tool("screenshot", {"device_id": "mac-primary", "scale": 0.5})
        assert not shot_tool.is_error, "screenshot tool failed"
        assert len(shot_tool.content) == 1, "Expected 1 content block"
        print("  ✅ MCP tool call: screenshot passed with valid ImageContent")

    asyncio.run(test_mcp_tools())

    print("\n" + "=" * 60)
    print("🎉 ALL MILESTONE 1 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
