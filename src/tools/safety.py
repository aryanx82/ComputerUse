"""
Safety & Emergency Control MCP Tools.
"""

from typing import Dict, Any
from src.safety.guardrails import guardrails

def register_safety_tools(mcp):

    @mcp.tool()
    def emergency_stop() -> str:
        """
        EMERGENCY KILL-SWITCH: Instantly halt all mouse, keyboard, touch, and application
        actions across all devices (Mac and Android).
        
        Once triggered, any interaction attempt will be strictly rejected until resume_control is called.
        """
        guardrails.set_emergency_stop(True)
        return "🚨 EMERGENCY STOP ACTIVATED. All device interactions are now locked down."

    @mcp.tool()
    def resume_control() -> str:
        """
        Resume normal device interaction after an emergency stop was triggered.
        """
        guardrails.set_emergency_stop(False)
        return "🟢 Emergency stop cleared. Normal device interactions are restored."

    @mcp.tool()
    def get_safety_status() -> Dict[str, Any]:
        """
        Get the current safety configuration, guardrail status, and emergency stop state.
        """
        return {
            "emergency_stop_active": guardrails.is_emergency_stopped(),
            "safety_mode": guardrails.mode,
            "max_actions_per_minute": guardrails.max_actions_per_minute,
            "audit_logging_enabled": True
        }
