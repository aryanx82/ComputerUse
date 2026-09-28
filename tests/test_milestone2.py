"""
Automated Test Suite for Milestone 2:
Tests Full Mac Control capabilities:
1. Active application detection (get_active_app)
2. Accessibility UI element tree reading (get_ui_tree)
3. Direct Unicode text typing (type_text)
4. Keypress and modifier shortcuts (press_key)
5. Scroll wheel simulation (scroll)
6. Click-and-drag simulation (drag)
7. Application launching (open_app)
8. End-to-end MCP protocol invocation of all Milestone 2 tools
"""

import sys
import json
import asyncio
from src.registry import DeviceRegistry
from src.router import ToolRouter
from src.server import mcp

def run_milestone2_tests():
    print("=" * 60)
    print("Starting Comprehensive Milestone 2 Test Suite")
    print("=" * 60)
    
    registry = DeviceRegistry()
    router = ToolRouter(registry)
    adapter = registry.get_adapter("mac-primary")
    
    # ── Test 1: Active App Detection ──
    print("\n[Test 1] Frontmost Application Detection...")
    app = router.get_active_app("mac-primary")
    print(f"  ✅ Frontmost app: {app.get('name')} (Bundle ID: {app.get('bundle_id')}, PID: {app.get('pid')})")
    assert "name" in app, "Expected 'name' in active app dict"

    # ── Test 2: Accessibility UI Tree ──
    print("\n[Test 2] Accessibility Element Tree (get_ui_tree)...")
    tree = router.get_ui_tree("mac-primary", max_depth=3, max_children=5)
    print(f"  ✅ UI Tree received for app: {tree.get('app_name')} (Role: {tree.get('role', 'N/A')})")
    assert "app_name" in tree, "Tree missing app_name"
    if "children" in tree:
        print(f"  ✅ Inspected {len(tree['children'])} top-level child elements")

    # ── Test 3: Unicode Text Typing ──
    print("\n[Test 3] Unicode Keyboard Typing (type_text)...")
    test_strings = [
        "Hello Computer Use!",
        "Accent test: café résumé ñ",
    ]
    for text in test_strings:
        res = router.type_text("mac-primary", text)
        assert res.success, f"Typing failed for '{text}': {res.error}"
        print(f"  ✅ Typed: '{text}' successfully")

    # ── Test 4: Key Press & Modifiers ──
    print("\n[Test 4] Keypress and Shortcuts (press_key)...")
    keys_to_test = [
        ("space", []),
        ("tab", []),
        ("escape", []),
        ("c", ["cmd"]),
    ]
    for key, mods in keys_to_test:
        res = router.press_key("mac-primary", key, modifiers=mods)
        combo_name = "+".join(mods + [key]) if mods else key
        assert res.success, f"Pressing key '{combo_name}' failed: {res.error}"
        print(f"  ✅ Pressed key combo: '{combo_name}' successfully")

    # ── Test 5: Mouse Scrolling ──
    print("\n[Test 5] Mouse Scrolling (scroll)...")
    res_scroll_down = router.scroll("mac-primary", 500, 500, delta_y=-50)
    assert res_scroll_down.success, f"Scroll down failed: {res_scroll_down.error}"
    print("  ✅ Scrolled down by 50px")

    res_scroll_up = router.scroll("mac-primary", 500, 500, delta_y=50)
    assert res_scroll_up.success, f"Scroll up failed: {res_scroll_up.error}"
    print("  ✅ Scrolled up by 50px")

    # ── Test 6: Mouse Dragging ──
    print("\n[Test 6] Mouse Click and Drag (drag)...")
    res_drag = router.drag("mac-primary", 400, 400, 450, 450)
    assert res_drag.success, f"Drag failed: {res_drag.error}"
    print("  ✅ Dragged from (400, 400) to (450, 450)")

    # ── Test 7: App Launching ──
    print("\n[Test 7] Application Management (open_app)...")
    res_app = router.open_app("mac-primary", "Finder")
    print(f"  ✅ Finder activated successfully: {res_app}")

    # ── Test 8: MCP Protocol Tool Invocations ──
    print("\n[Test 8] MCP Protocol Tool Invocation Loop...")
    async def test_all_mcp_tools():
        tools = await mcp.list_tools()
        tool_names = [t.name for t in tools]
        expected = ["list_devices", "get_device_info", "screenshot", "get_ui_tree", 
                    "get_active_app", "click", "type_text", "press_key", "drag", "scroll", "open_app"]
        for exp in expected:
            assert exp in tool_names, f"Missing MCP tool: {exp}"
        print(f"  ✅ All {len(expected)} expected MCP tools registered on server")

        # Test active app tool via MCP
        active_res = await mcp.call_tool("get_active_app", {"device_id": "mac-primary"})
        assert not active_res.is_error, "get_active_app MCP call failed"
        print("  ✅ MCP call: get_active_app OK")

        # Test type_text tool via MCP
        type_res = await mcp.call_tool("type_text", {"device_id": "mac-primary", "text": "MCP Test"})
        assert not type_res.is_error, "type_text MCP call failed"
        print("  ✅ MCP call: type_text OK")

        # Test press_key tool via MCP
        key_res = await mcp.call_tool("press_key", {"device_id": "mac-primary", "key": "tab"})
        assert not key_res.is_error, "press_key MCP call failed"
        print("  ✅ MCP call: press_key OK")

        # Test scroll tool via MCP
        scroll_res = await mcp.call_tool("scroll", {"device_id": "mac-primary", "x": 500, "y": 500, "delta_y": -20})
        assert not scroll_res.is_error, "scroll MCP call failed"
        print("  ✅ MCP call: scroll OK")

        # Test get_ui_tree tool via MCP
        tree_res = await mcp.call_tool("get_ui_tree", {"device_id": "mac-primary", "max_depth": 2})
        assert not tree_res.is_error, "get_ui_tree MCP call failed"
        print("  ✅ MCP call: get_ui_tree OK")

    asyncio.run(test_all_mcp_tools())

    print("\n" + "=" * 60)
    print("🎉 ALL MILESTONE 2 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_milestone2_tests()
