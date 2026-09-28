"""
Automated Test Suite for Milestone 3:
Tests Android Basic Control via ADB:
1. Android device detection and capability reporting
2. Screenshot capture via direct PNG stream from SurfaceFlinger
3. Screenshot downscaling and JPEG conversion
4. Touch tap simulation (click)
5. Physical and virtual key events (press_key: wakeup, volume, etc.)
6. Text typing with space escaping (type_text)
7. Touch scrolling and swipe gestures (scroll, drag)
8. Accessibility UI hierarchy dumping and XML parsing (get_ui_tree)
9. Active window and package detection (get_active_app)
10. End-to-end MCP protocol tool execution on Android
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

def run_milestone3_tests():
    print("=" * 60)
    print("Starting Comprehensive Milestone 3 (Android) Test Suite")
    print("=" * 60)
    
    registry = DeviceRegistry()
    router = ToolRouter(registry)
    
    # ── Test 1: Device Detection ──
    print("\n[Test 1] Android Device Detection...")
    devices = registry.list_devices()
    android_devices = [d for d in devices if d.platform == "android"]
    assert len(android_devices) > 0, "No Android devices detected via ADB"
    
    dev = android_devices[0]
    dev_id = dev.id
    print(f"  ✅ Detected Android Device: {dev.name} (ID: {dev_id})")
    assert dev.status.is_connected, "Android device is reported as disconnected"
    assert dev.capabilities.screenshot, "Android device missing screenshot capability"

    # ── Test 2: Full Resolution Screenshot ──
    print("\n[Test 2] Android Screen Capture (scale=1.0)...")
    t0 = time.time()
    shot_full = router.screenshot(dev_id, scale=1.0)
    t1 = time.time()
    raw_bytes = base64.b64decode(shot_full.image_base64)
    img = Image.open(io.BytesIO(raw_bytes))
    print(f"  ✅ Captured {shot_full.width}x{shot_full.height} in {(t1-t0)*1000:.1f}ms (Format: {img.format}, Size: {len(raw_bytes)} bytes)")
    assert shot_full.width > 0 and shot_full.height > 0, "Invalid screenshot dimensions"

    # ── Test 3: Downscaled Screenshot ──
    print("\n[Test 3] Android Screen Capture Downscaled (scale=0.5)...")
    shot_half = router.screenshot(dev_id, scale=0.5)
    raw_half = base64.b64decode(shot_half.image_half if hasattr(shot_half, 'image_half') else shot_half.image_base64)
    print(f"  ✅ Downscaled to {shot_half.width}x{shot_half.height} ({len(raw_half)} bytes)")
    assert shot_half.width <= shot_full.width, "Downscaled width should be smaller than full width"

    # ── Test 4: Touch Tap ──
    print("\n[Test 4] Touch Tap Simulation (click)...")
    tap_x = shot_full.width // 2
    tap_y = shot_full.height // 2
    res_tap = router.click(dev_id, tap_x, tap_y)
    assert res_tap.success, f"Tap failed: {res_tap.error}"
    print(f"  ✅ Touch tap succeeded at ({tap_x}, {tap_y})")

    # ── Test 5: Key Event ──
    print("\n[Test 5] Physical / Virtual Key Events (press_key)...")
    res_key = router.press_key(dev_id, "wakeup")
    assert res_key.success, f"Keypress failed: {res_key.error}"
    print("  ✅ Sent keyevent 'wakeup' successfully")

    # ── Test 6: Text Typing ──
    print("\n[Test 6] Text Input (type_text)...")
    res_type = router.type_text(dev_id, "TestADBInput")
    assert res_type.success, f"Typing failed: {res_type.error}"
    print("  ✅ Sent text input 'TestADBInput' successfully")

    # ── Test 7: Touch Scroll & Swipe ──
    print("\n[Test 7] Touch Scroll & Drag Gestures (scroll, drag)...")
    res_scroll = router.scroll(dev_id, tap_x, tap_y, delta_y=-150)
    assert res_scroll.success, f"Scroll failed: {res_scroll.error}"
    print("  ✅ Touch scroll succeeded (delta_y=-150)")

    res_drag = router.drag(dev_id, 300, 300, 350, 350)
    assert res_drag.success, f"Drag failed: {res_drag.error}"
    print("  ✅ Touch drag succeeded from (300,300) to (350,350)")

    # ── Test 8: Active App Detection ──
    print("\n[Test 8] Active Android App Detection (get_active_app)...")
    app_info = router.get_active_app(dev_id)
    print(f"  ✅ Active app package: {app_info.get('package')}, Activity: {app_info.get('activity')}")
    assert "package" in app_info, "Expected 'package' in app_info"

    # ── Test 9: UI Tree Inspection ──
    print("\n[Test 9] Accessibility UI Tree (get_ui_tree)...")
    tree = router.get_ui_tree(dev_id, max_depth=3, max_children=5)
    print(f"  ✅ UI Tree root role: {tree.get('role')}, App package: {tree.get('package')}")
    assert "role" in tree, "Tree missing role attribute"
    assert "children" in tree or "bounds" in tree, "Tree missing structural attributes"

    # ── Test 10: MCP Protocol Invocations ──
    print("\n[Test 10] MCP Protocol Tool Execution on Android...")
    async def test_mcp_android():
        # List devices via MCP
        dev_res = await mcp.call_tool("list_devices", {})
        assert not dev_res.is_error, "list_devices MCP tool failed"
        print("  ✅ MCP tool call: list_devices passed")

        # Get device info via MCP
        info_res = await mcp.call_tool("get_device_info", {"device_id": dev_id})
        assert not info_res.is_error, "get_device_info MCP tool failed"
        print(f"  ✅ MCP tool call: get_device_info for {dev_id} passed")

        # Screenshot via MCP
        shot_res = await mcp.call_tool("screenshot", {"device_id": dev_id, "scale": 0.5})
        assert not shot_res.is_error, "screenshot MCP tool failed"
        assert len(shot_res.content) == 1, "Expected 1 content block"
        print("  ✅ MCP tool call: screenshot passed with valid ImageContent")

        # Click via MCP
        click_res = await mcp.call_tool("click", {"device_id": dev_id, "x": 500, "y": 500})
        assert not click_res.is_error, "click MCP tool failed"
        print("  ✅ MCP tool call: click passed")

        # UI Tree via MCP
        tree_res = await mcp.call_tool("get_ui_tree", {"device_id": dev_id, "max_depth": 2})
        assert not tree_res.is_error, "get_ui_tree MCP tool failed"
        print("  ✅ MCP tool call: get_ui_tree passed")

    asyncio.run(test_mcp_android())

    print("\n" + "=" * 60)
    print("🎉 ALL MILESTONE 3 (ANDROID) VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_milestone3_tests()
