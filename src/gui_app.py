"""
computerUse Desktop Application — Dynamic Chatbot System with Full History
Runs a native macOS WebKit window displaying OpenAI Codex UI,
with dynamic chat sessions, persistent history, and Groq/Direct execution.
"""

import os
import sys
import json
import time
import webview

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from src.registry import DeviceRegistry
from src.router import ToolRouter
from src.safety.guardrails import guardrails
from src.agent.groq_agent import GroqAgent

CHATS_FILE_PATH = os.path.expanduser("~/.computer-use-tool/chat_sessions.json")


class JsApi:
    """JavaScript API bridge exposed to the webview window."""

    def __init__(self, holder):
        self.holder = holder
        self.registry = DeviceRegistry()
        self.router = ToolRouter(self.registry)
        self.agent = GroqAgent(self.router, self.registry)
        self.target_device = "mac-primary"
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(os.path.dirname(CHATS_FILE_PATH), exist_ok=True)
        if not os.path.exists(CHATS_FILE_PATH):
            with open(CHATS_FILE_PATH, "w") as f:
                json.dump([], f)

    # ── Chat Session Persistence ──────────────────────────────────────

    def get_all_chats(self):
        """Retrieve all stored chat sessions from disk."""
        try:
            with open(CHATS_FILE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def save_chat_session(self, chat_session):
        """Save or update a specific chat session."""
        try:
            chats = self.get_all_chats()
            chat_id = chat_session.get("id")
            
            # Find and update or prepend
            existing_idx = None
            for idx, c in enumerate(chats):
                if c.get("id") == chat_id:
                    existing_idx = idx
                    break

            if existing_idx is not None:
                chats[existing_idx] = chat_session
            else:
                chats.insert(0, chat_session)

            with open(CHATS_FILE_PATH, "w") as f:
                json.dump(chats, f, indent=2)
            return True
        except Exception as e:
            print("Error saving chat session:", e)
            return False

    def delete_chat_session(self, chat_id):
        """Delete a chat session by ID."""
        try:
            chats = self.get_all_chats()
            chats = [c for c in chats if c.get("id") != chat_id]
            with open(CHATS_FILE_PATH, "w") as f:
                json.dump(chats, f, indent=2)
            return True
        except Exception as e:
            print("Error deleting chat session:", e)
            return False

    # ── Message Processing ────────────────────────────────────────────

    def send_message(self, message: str, device_id: str, chat_id: str = "") -> dict:
        self.target_device = device_id or "mac-primary"
        collected_actions = []

        def _action_cb(tool_name: str, desc: str):
            collected_actions.append({"tool": tool_name, "desc": desc})
            win = self.holder.get("window")
            if win:
                safe_desc = desc.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
                try:
                    win.evaluate_js(f"window.onPyAction('{tool_name}', '{safe_desc}')")
                except Exception:
                    pass

        try:
            reply = self.agent.process_message(
                user_message=message,
                target_device=self.target_device,
                on_action_callback=_action_cb
            )
            return {
                "success": True,
                "reply": reply,
                "actions": collected_actions
            }
        except Exception as e:
            return {
                "success": False,
                "reply": f"❌ Error executing instruction: {str(e)}",
                "actions": collected_actions
            }

    # ── Settings ──────────────────────────────────────────────────────

    def get_settings(self):
        return {
            "api_key": self.agent.load_api_key(),
            "has_key": bool(self.agent.load_api_key()),
            "target_device": self.target_device
        }

    def save_settings(self, api_key: str, target_device: str):
        self.agent.save_api_key(api_key)
        self.agent.api_key = api_key
        self.target_device = target_device
        return True


def run_app():
    ui_dir = os.path.join(SCRIPT_DIR, "src", "ui")
    index_path = os.path.join(ui_dir, "index.html")

    holder = {}
    api = JsApi(holder)

    window = webview.create_window(
        title="Codex",
        url=index_path,
        js_api=api,
        width=1240,
        height=820,
        min_size=(960, 620),
        background_color="#1e1e20"
    )
    holder["window"] = window

    webview.start(debug=False)


if __name__ == "__main__":
    run_app()
