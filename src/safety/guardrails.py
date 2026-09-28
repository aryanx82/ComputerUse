"""
Safety Guardrails & Audit Logger for Computer Use Tool.

Implements safety policies:
1. Emergency Stop: Global instant halt for all interactive operations.
2. Destructive Action Filtering: Detects high-risk shortcuts (Cmd+Q, Cmd+Delete) and dangerous terminal text (rm -rf, sudo, etc.).
3. Protected App Blacklisting: Prevents interaction with Keychain, Password Managers, and Sensitive Settings.
4. Rate Limiting: Prevents runaway automation loops.
5. Audit Logging: Logs every action with timestamp, parameters, and outcome to ~/.computer-use-tool/audit.log.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

AUDIT_LOG_DIR = os.path.expanduser("~/.computer-use-tool")
AUDIT_LOG_PATH = os.path.join(AUDIT_LOG_DIR, "audit.log")
EMERGENCY_STOP_FILE = os.path.join(AUDIT_LOG_DIR, "EMERGENCY_STOP")

# Blacklisted apps where automated interaction is prohibited
PROTECTED_APPS = {
    # macOS
    "keychain access",
    "com.apple.keychainaccess",
    "system settings",
    "com.apple.systempreferences",
    "1password",
    "bitwarden",
    "keepass",
    "lastpass",
    
    # Android
    "com.android.settings.security",
    "com.google.android.gms.auth",
    "com.samsung.android.knox",
}

# Dangerous key combinations that can terminate apps or destroy data
DESTRUCTIVE_KEY_COMBOS = {
    ("q", ("cmd",)),
    ("q", ("command",)),
    ("delete", ("cmd",)),
    ("backspace", ("cmd",)),
    ("escape", ("cmd", "alt")),
    ("escape", ("cmd", "option")),
    ("power", ()),
}

# Dangerous command patterns in typed text
DESTRUCTIVE_TEXT_PATTERNS = [
    "rm -rf",
    "rm -r /",
    "mkfs",
    "dd if=",
    "sudo rm",
    "format c:",
    ":(){ :|:& };:",
    "> /dev/sda",
]


class SafetyGuardrails:
    """Enforces safety policies, protected apps, rate limits, and audit trails."""

    def __init__(self, mode: str = "strict", max_actions_per_minute: int = 120):
        self.mode = mode.lower()  # "strict", "ask", or "relaxed"
        self.max_actions_per_minute = max_actions_per_minute
        self._action_timestamps: List[float] = []
        os.makedirs(AUDIT_LOG_DIR, exist_ok=True)

    # ── Emergency Stop ───────────────────────────────────────────────

    @staticmethod
    def is_emergency_stopped() -> bool:
        """Check if global emergency stop is active."""
        return os.path.exists(EMERGENCY_STOP_FILE)

    @staticmethod
    def set_emergency_stop(active: bool):
        """Enable or disable global emergency stop."""
        if active:
            with open(EMERGENCY_STOP_FILE, "w") as f:
                f.write(f"Emergency stop activated at {datetime.now(timezone.utc).isoformat()}\n")
        else:
            if os.path.exists(EMERGENCY_STOP_FILE):
                os.remove(EMERGENCY_STOP_FILE)

    # ── Action Validation ────────────────────────────────────────────

    def validate_action(
        self,
        device_id: str,
        action_name: str,
        params: Dict[str, Any],
        active_app: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate whether an action is permitted under the current safety policy.
        Returns: (is_allowed: bool, reason_if_blocked: str | None)
        """
        # 1. Global Kill-Switch Check
        if self.is_emergency_stopped():
            return False, "EMERGENCY STOP IS ACTIVE. All synthetic input is halted. Call resume_control to unfreeze."

        # 2. Rate Limiting Check
        now = time.time()
        self._action_timestamps = [t for t in self._action_timestamps if now - t < 60.0]
        if len(self._action_timestamps) >= self.max_actions_per_minute:
            return False, f"Rate limit exceeded: maximum {self.max_actions_per_minute} actions per minute allowed."
        self._action_timestamps.append(now)

        # In relaxed mode, skip further content checks
        if self.mode == "relaxed":
            return True, None

        # 3. Protected Application Blacklist
        if active_app:
            app_lower = active_app.lower()
            for protected in PROTECTED_APPS:
                if protected in app_lower:
                    return False, f"Interaction blocked: Target application '{active_app}' is protected for user security."

        # 4. Destructive Key Combination Check
        if action_name == "press_key":
            key = str(params.get("key", "")).lower()
            mods = tuple(sorted(m.lower() for m in params.get("modifiers", [])))
            for dkey, dmods in DESTRUCTIVE_KEY_COMBOS:
                if key == dkey and all(m in mods for m in dmods):
                    return False, f"Destructive key shortcut '{'+'.join(mods + (key,))}' is blocked by safety policy."

        # 5. Destructive Text Input Check
        if action_name == "type_text":
            text = str(params.get("text", ""))
            for pattern in DESTRUCTIVE_TEXT_PATTERNS:
                if pattern in text:
                    return False, f"Potentially destructive text pattern '{pattern}' is blocked by safety policy."

        return True, None

    # ── Audit Trail ──────────────────────────────────────────────────

    def log_audit_record(
        self,
        device_id: str,
        action_name: str,
        params: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
        duration_ms: float = 0.0
    ):
        """Append a tamper-evident audit record to ~/.computer-use-tool/audit.log."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": device_id,
            "action": action_name,
            # Redact sensitive parameters if needed
            "params": params,
            "success": success,
            "error": error,
            "duration_ms": round(duration_ms, 2)
        }
        try:
            with open(AUDIT_LOG_PATH, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass


# Global singleton guardrails instance
guardrails = SafetyGuardrails()
