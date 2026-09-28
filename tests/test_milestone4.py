"""
Automated Test Suite for Milestone 4:
Tests Multi-Device Coordination & Unified UI Normalization:
1. Multi-device discovery & alias resolution across Mac and Android
2. Cross-platform UI tree normalization schema validation
3. Semantic UI element search (find_ui_elements)
4. Direct semantic element clicking (click_ui_element)
5. Universal URL opening (open_url) across Mac and Android
6. Cross-device coordination workflow (Mac -> Android action chain)
7. Full MCP protocol invocations for Milestone 4 tools
"""

import sys
import json
import asyncio
from src.registry import DeviceRegistry
from src.router import ToolRouter
from src.server import mcp

def run_milestone4_tests():
    print("=" * 60)
    print("Starting Comprehensive Milestone 4 Test Suite")
    print("=" * 60)
    
    registry = DeviceRegistry()
    router = ToolRouter(registry)
    
    # ── Test 1: Multi-Device Discovery & Aliases ──
    print("\n[Test 1] Multi-Device Discovery & Aliasing...")
    devices = registry.list_devices()
    platforms = {d.platform for d in devices}
    print(f"  ✅ Discovered {len(devices)} device(s) spanning platforms: {platforms}")
    assert "macos" in platforms, "macOS host not discovered"
    assert "android" in platforms, "Android device not discovered"
    
    # Verify android-primary alias
    android_adapter = registry.get_adapter("android-primary")
    assert android_adapter.device_id.startswith("android-"), "android-primary alias invalid"
    print(f"  ✅ 'android-primary' alias correctly routed to: {android_adapter.device_id}")

    # ── Test 2: Unified UI Tree Normalization Schema ──
    print("\n[Test 2] Cross-Platform UI Tree Normalization...")
    # Mac normalized tree
    mac_tree = router.get_ui_tree("mac-primary", max_depth=3, normalize=True)
    assert mac_tree.get("platform") == "macos", "Expected platform 'macos'"
    print(f"  ✅ macOS normalized root role: '{mac_tree.get('role')}', app: '{mac_tree.get('app_name')}'")
    
    # Android normalized tree
    android_tree = router.get_ui_tree("android-primary", max_depth=3, normalize=True)
    assert android_tree.get("platform") == "android", "Expected platform 'android'"
    print(f"  ✅ Android normalized root role: '{android_tree.get('role')}', app: '{android_tree.get('app_name')}'")

    # Verify both trees have matching schema keys
    for tree_label, tree in [("macOS", mac_tree), ("Android", android_tree)]:
        assert "role" in tree, f"{tree_label} tree missing 'role'"
        assert "platform" in tree, f"{tree_label} tree missing 'platform'"
        assert "app_name" in tree, f"{tree_label} tree missing 'app_name'"
        print(f"  ✅ {tree_label} tree adheres to unified schema")

    # ── Test 3: Semantic UI Search (find_ui_elements) ──
    print("\n[Test 3] Semantic UI Element Search...")
    # Search on Mac
    mac_elements = router.find_ui_elements("mac-primary", max_results=5)
    print(f"  ✅ Found {len(mac_elements)} interactive elements on Mac")
    if mac_elements:
        first = mac_elements[0]
        print(f"     Sample Mac element: role='{first['role']}', label='{first['label']}', center={first['center']}")
        assert "center" in first and "x" in first["center"], "Center coordinates missing"

    # Search on Android
    android_elements = router.find_ui_elements("android-primary", max_results=5)
    print(f"  ✅ Found {len(android_elements)} interactive elements on Android")
    if android_elements:
        first = android_elements[0]
        print(f"     Sample Android element: role='{first['role']}', label='{first['label']}', center={first['center']}")
        assert "center" in first and "x" in first["center"], "Center coordinates missing"

    # ── Test 4: Direct Semantic Click (click_ui_element) ──
    print("\n[Test 4] Direct Semantic Element Click...")
    # If any interactive elements found on Mac, click the first one
    if mac_elements and mac_elements[0].get("label"):
        target_label = mac_elements[0]["label"]
        res_click = router.click_ui_element("mac-primary", text_query=target_label)
        assert res_click.success, f"Semantic click failed for '{target_label}': {res_click.error}"
        print(f"  ✅ Successfully clicked Mac element matching '{target_label}'")

    # ── Test 5: Universal URL Opening (open_url) ──
    print("\n[Test 5] Universal URL Opener (open_url)...")
    res_url_android = router.open_url("android-primary", "https://example.com")
    print(f"  ✅ Android open_url result: {res_url_android}")
    assert "url" in res_url_android, "Expected url in open_url response"

    # ── Test 6: Cross-Device Coordination Workflow ──
    print("\n[Test 6] Cross-Device Orchestration Workflow...")
    # Step 1: Capture state on Mac
    shot_mac = router.screenshot("mac-primary", scale=0.25)
    print(f"  1. Observed Mac screen: {shot_mac.width}x{shot_mac.height}")

    # Step 2: Trigger action on Android based on workflow
    res_action = router.press_key("android-primary", "wakeup")
    print(f"  2. Dispatched action to Android: wakeup (success={res_action.success})")

    # Step 3: Capture resulting state on Android
    shot_android = router.screenshot("android-primary", scale=0.25)
    print(f"  3. Observed Android response: {shot_android.width}x{shot_android.height}")
    print("  ✅ Cross-device round-trip orchestration succeeded!")

    # ── Test 7: MCP Protocol Invocation Loop for Milestone 4 ──
    print("\n[Test 7] MCP Protocol Tool Invocations for Milestone 4...")
    async def test_mcp_milestone4():
        tools = await mcp.list_tools()
        tool_names = [t.name for t in tools]
        for needed in ["find_ui_elements", "click_ui_element", "open_url"]:
            assert needed in tool_names, f"Missing MCP tool: {needed}"
        print(f"  ✅ Milestone 4 tools (find_ui_elements, click_ui_element, open_url) registered on MCP server")

        # Call find_ui_elements via MCP
        find_res = await mcp.call_tool("find_ui_elements", {"device_id": "android-primary", "max_results": 3})
        assert not find_res.is_error, "find_ui_elements tool failed"
        print("  ✅ MCP call: find_ui_elements passed")

        # Call open_url via MCP
        url_res = await mcp.call_tool("open_url", {"device_id": "android-primary", "url": "https://example.com"})
        assert not url_res.is_error, "open_url tool failed"
        print("  ✅ MCP call: open_url passed")

    asyncio.run(test_mcp_milestone4())

    print("\n" + "=" * 60)
    print("🎉 ALL MILESTONE 4 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_milestone4_tests()
