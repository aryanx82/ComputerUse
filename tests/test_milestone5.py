"""
Automated Test Suite for Milestone 5:
Tests Optimization, Latency & Safety Hardening:
1. Persistent socket connection performance (rapid IPC benchmark)
2. Destructive key combination blocking (e.g. Cmd+Q)
3. Destructive text pattern blocking (e.g. rm -rf)
4. Protected application blacklisting (e.g. Keychain Access)
5. Global Emergency Stop & Resume (kill-switch)
6. Audit log generation and tamper-evident record structure
7. MCP protocol tools: emergency_stop, resume_control, get_safety_status
"""

import sys
import os
import json
import time
import asyncio
from src.registry import DeviceRegistry
from src.router import ToolRouter
from src.safety.guardrails import guardrails, AUDIT_LOG_PATH
from src.server import mcp

def run_milestone5_tests():
    print("=" * 60)
    print("Starting Comprehensive Milestone 5 Test Suite")
    print("=" * 60)
    
    registry = DeviceRegistry()
    router = ToolRouter(registry)
    
    # ── Test 1: Persistent Socket Latency Benchmark ──
    print("\n[Test 1] Persistent Socket Connection Performance...")
    # Ensure fresh connection
    t0 = time.time()
    num_calls = 5
    for i in range(num_calls):
        res = router.click("mac-primary", 200, 200)
        assert res.success, f"Persistent click {i} failed"
    total_time = (time.time() - t0) * 1000
    avg_time = total_time / num_calls
    print(f"  ✅ Executed {num_calls} sequential calls in {total_time:.1f}ms (Average: {avg_time:.1f}ms per call)")
    assert avg_time < 150.0, "IPC round-trip latency too high"

    # ── Test 2: Destructive Key Combination Blocking ──
    print("\n[Test 2] Destructive Key Combination Blocking...")
    res_cmd_q = router.press_key("mac-primary", "q", modifiers=["cmd"])
    assert not res_cmd_q.success, "Cmd+Q should have been blocked by safety guardrails"
    print(f"  ✅ Blocked destructive Cmd+Q: '{res_cmd_q.error}'")

    res_cmd_del = router.press_key("mac-primary", "delete", modifiers=["cmd"])
    assert not res_cmd_del.success, "Cmd+Delete should have been blocked"
    print(f"  ✅ Blocked destructive Cmd+Delete: '{res_cmd_del.error}'")

    # ── Test 3: Destructive Text Pattern Blocking ──
    print("\n[Test 3] Destructive Text Input Blocking...")
    res_text = router.type_text("mac-primary", "rm -rf /")
    assert not res_text.success, "'rm -rf /' should have been blocked"
    print(f"  ✅ Blocked destructive text: '{res_text.error}'")

    # ── Test 4: Protected Application Blacklisting ──
    print("\n[Test 4] Protected Application Blacklisting...")
    try:
        router.open_app("mac-primary", "Keychain Access")
        assert False, "Opening Keychain Access should have raised PermissionError"
    except PermissionError as e:
        print(f"  ✅ Blocked launch of protected app: '{e}'")

    # ── Test 5: Global Emergency Stop & Resume (Kill-Switch) ──
    print("\n[Test 5] Global Emergency Stop (Kill-Switch)...")
    # Activate kill-switch
    guardrails.set_emergency_stop(True)
    assert guardrails.is_emergency_stopped(), "Emergency stop should be active"
    
    # Attempt action while halted
    res_blocked = router.click("mac-primary", 100, 100)
    assert not res_blocked.success, "Action should be blocked while emergency stop is active"
    print(f"  ✅ Action rejected during emergency stop: '{res_blocked.error}'")

    # Resume control
    guardrails.set_emergency_stop(False)
    assert not guardrails.is_emergency_stopped(), "Emergency stop should be inactive"
    res_resumed = router.click("mac-primary", 100, 100)
    assert res_resumed.success, "Action should succeed after resuming control"
    print("  ✅ Action succeeded after clearing emergency stop")

    # ── Test 6: Audit Log Verification ──
    print("\n[Test 6] Audit Trail Verification (~/.computer-use-tool/audit.log)...")
    assert os.path.exists(AUDIT_LOG_PATH), "Audit log file does not exist"
    with open(AUDIT_LOG_PATH, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) > 0, "Audit log is empty"
    last_record = json.loads(lines[-1])
    print(f"  ✅ Last audit record: action='{last_record.get('action')}', device='{last_record.get('device_id')}', success={last_record.get('success')}")
    assert "timestamp" in last_record, "Audit record missing timestamp"
    assert "action" in last_record, "Audit record missing action"

    # ── Test 7: MCP Protocol Safety Tools ──
    print("\n[Test 7] MCP Protocol Safety Tools Execution...")
    async def test_mcp_safety():
        # Query safety status
        status_res = await mcp.call_tool("get_safety_status", {})
        assert not status_res.is_error, "get_safety_status tool failed"
        print("  ✅ MCP call: get_safety_status passed")

        # Trigger emergency stop via MCP
        stop_res = await mcp.call_tool("emergency_stop", {})
        assert not stop_res.is_error, "emergency_stop tool failed"
        assert guardrails.is_emergency_stopped(), "Emergency stop was not set via MCP"
        print("  ✅ MCP call: emergency_stop activated kill-switch")

        # Resume control via MCP
        resume_res = await mcp.call_tool("resume_control", {})
        assert not resume_res.is_error, "resume_control tool failed"
        assert not guardrails.is_emergency_stopped(), "Emergency stop was not cleared via MCP"
        print("  ✅ MCP call: resume_control cleared kill-switch")

    asyncio.run(test_mcp_safety())

    print("\n" + "=" * 60)
    print("🎉 ALL MILESTONE 5 (SAFETY & OPTIMIZATION) TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_milestone5_tests()
