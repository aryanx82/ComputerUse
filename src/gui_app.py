"""
computerUse Desktop Application — OpenAI Codex Style UI
Runs a native macOS WebKit window displaying the exact Codex UI,
interfacing directly with Groq AI Agent and Computer Use ToolRouter.
"""

import os
import sys
import json
import webview

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from src.registry import DeviceRegistry
from src.router import ToolRouter
from src.safety.guardrails import guardrails
from src.agent.groq_agent import GroqAgent


class JsApi:
    """JavaScript API bridge exposed to the webview window."""

    def __init__(self, holder):
        self.holder = holder
        self.registry = DeviceRegistry()
        self.router = ToolRouter(self.registry)
        self.agent = GroqAgent(self.router, self.registry)
        self.target_device = "mac-primary"

    def send_message(self, message: str, device_id: str) -> str:
        self.target_device = device_id or "mac-primary"

        def _action_cb(tool_name: str, desc: str):
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
            return reply
        except Exception as e:
            return f"❌ Error executing instruction: {str(e)}"

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

    # Start native macOS Cocoa WebKit loop
    webview.start(debug=False)


if __name__ == "__main__":
    run_app()
