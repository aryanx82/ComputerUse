"""
Groq AI Agent for Computer Use Tool.
Orchestrates natural language commands via Groq API tool-calling (Llama 3.3 70B),
interfacing directly with ToolRouter to observe and interact with Mac and Android devices.
Includes built-in direct NLP fallback when no API key is configured.
"""

import os
import sys
import json
import time
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Callable

from src.router import ToolRouter
from src.registry import DeviceRegistry

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
KEY_FILE_PATH = os.path.expanduser("~/.computer-use-tool/groq_key.txt")

# Tool schemas provided to Groq for function calling
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launch or bring to focus an application by name on the Mac or Android device.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application (e.g. 'Blender', 'Calculator', 'Safari', 'Notes', 'TextEdit', 'Chrome')."
                    },
                    "device_id": {
                        "type": "string",
                        "description": "Target device ('mac-primary' or 'android-primary'). Defaults to 'mac-primary'.",
                        "default": "mac-primary"
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text into the currently focused window or text field.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The exact text string to type."
                    },
                    "device_id": {
                        "type": "string",
                        "description": "Target device ('mac-primary' or 'android-primary').",
                        "default": "mac-primary"
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a keyboard shortcut or special key (e.g. 'enter', 'tab', 'escape', 'space', 'c' with modifier 'cmd').",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key to press (e.g. 'enter', 'return', 'tab', 'escape', 'space', 'c', 'v', 'n', 'home', 'back')."
                    },
                    "modifiers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional keyboard modifiers (e.g. ['cmd'], ['shift'], ['alt'], ['ctrl']).",
                        "default": []
                    },
                    "device_id": {
                        "type": "string",
                        "description": "Target device ('mac-primary' or 'android-primary').",
                        "default": "mac-primary"
                    }
                },
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click at specific screen pixel coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Horizontal pixel coordinate."},
                    "y": {"type": "integer", "description": "Vertical pixel coordinate."},
                    "button": {
                        "type": "string",
                        "enum": ["left", "right"],
                        "description": "Mouse button.",
                        "default": "left"
                    },
                    "click_count": {"type": "integer", "description": "1 for single click, 2 for double click.", "default": 1},
                    "device_id": {"type": "string", "description": "Target device.", "default": "mac-primary"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_ui_element",
            "description": "Find and click a UI button or element by its visible text or accessibility label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Label, text, or title of the element to click (e.g. 'File', 'Save', 'Done', 'Search')."
                    },
                    "device_id": {"type": "string", "description": "Target device.", "default": "mac-primary"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a website URL in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to open (e.g. 'https://google.com')."},
                    "device_id": {"type": "string", "description": "Target device.", "default": "mac-primary"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll down or up on the page or window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down"],
                        "description": "Direction to scroll.",
                        "default": "down"
                    },
                    "device_id": {"type": "string", "description": "Target device.", "default": "mac-primary"}
                },
                "required": ["direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Capture a live screenshot of the device screen to observe its current state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Target device.", "default": "mac-primary"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_app",
            "description": "Get the name and process information of the frontmost active application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Target device.", "default": "mac-primary"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_devices",
            "description": "List all connected hardware devices (Mac, Android tablet, phone).",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]


class GroqAgent:
    """Agent that handles user instructions, plans actions, and calls Computer Use tools."""

    def __init__(self, router: ToolRouter, registry: DeviceRegistry):
        self.router = router
        self.registry = registry
        self.api_key = self.load_api_key()
        self.conversation_history: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are the Computer Use AI Assistant. You control the user's Mac and Android devices.\n"
                    "You can see the screen, open applications (like Blender, Calculator, Notes, Chrome, etc.), "
                    "type text, press shortcut keys, click buttons, scroll, and navigate URLs.\n\n"
                    "Guidelines:\n"
                    "1. When asked to open or do something in an app (e.g. 'open Blender' or 'open Calculator and calculate 2+2'), "
                    "call the relevant tools immediately.\n"
                    "2. Always pick the appropriate device_id (usually 'mac-primary' unless the user specifies Android/tablet).\n"
                    "3. Keep your conversational responses concise, clear, and helpful.\n"
                    "4. If an action fails or the app is not installed, explain clearly to the user."
                )
            }
        ]

    # ── Key Management ────────────────────────────────────────────────

    @staticmethod
    def load_api_key() -> str:
        """Load API key from environment variable or stored file."""
        if os.environ.get("GROQ_API_KEY"):
            return os.environ["GROQ_API_KEY"].strip()
        if os.path.exists(KEY_FILE_PATH):
            try:
                with open(KEY_FILE_PATH, "r") as f:
                    return f.read().strip()
            except Exception:
                pass
        return ""

    @staticmethod
    def save_api_key(key: str):
        """Save API key securely to disk."""
        os.makedirs(os.path.dirname(KEY_FILE_PATH), exist_ok=True)
        with open(KEY_FILE_PATH, "w") as f:
            f.write(key.strip())

    # ── Tool Execution Dispatcher ────────────────────────────────────

    def execute_tool(self, name: str, args: Dict[str, Any], default_device: str = "mac-primary") -> Dict[str, Any]:
        """Execute a tool call requested by Groq or by the fallback parser."""
        dev_id = args.get("device_id") or default_device

        try:
            if name == "open_app":
                app_name = args.get("app_name", "").strip()
                res = self.router.open_app(dev_id, app_name)
                return {"success": True, "result": f"Launched '{app_name}' on {dev_id}", "data": res}

            elif name == "open_url":
                url = args.get("url", "").strip()
                res = self.router.open_url(dev_id, url)
                return {"success": True, "result": f"Opened URL {url} on {dev_id}"}

            elif name == "type_text":
                text = args.get("text", "")
                res = self.router.type_text(dev_id, text)
                return {"success": res.success, "result": f"Typed '{text}'", "error": res.error}

            elif name == "press_key":
                key = args.get("key", "")
                mods = args.get("modifiers", [])
                res = self.router.press_key(dev_id, key=key, modifiers=mods)
                mod_str = "+".join(mods + [key]) if mods else key
                return {"success": res.success, "result": f"Pressed key '{mod_str}'", "error": res.error}

            elif name == "click":
                x = int(args.get("x", 0))
                y = int(args.get("y", 0))
                button = args.get("button", "left")
                cnt = int(args.get("click_count", 1))
                res = self.router.click(dev_id, x, y, button=button, click_count=cnt)
                return {"success": res.success, "result": f"Clicked at ({x}, {y})", "error": res.error}

            elif name == "click_ui_element":
                query = args.get("query", "")
                res = self.router.click_ui_element(dev_id, query)
                return {"success": res.success, "result": f"Clicked element matching '{query}'", "error": res.error}

            elif name == "scroll":
                direction = args.get("direction", "down").lower()
                dy = 100 if "up" in direction else -100
                res = self.router.scroll(dev_id, delta_y=dy)
                return {"success": res.success, "result": f"Scrolled {direction}", "error": res.error}

            elif name == "screenshot":
                shot = self.router.screenshot(dev_id, scale=0.5)
                return {
                    "success": True,
                    "result": f"Screenshot captured ({shot.width}x{shot.height})",
                    "screenshot_b64": shot.image_base64
                }

            elif name == "get_active_app":
                res = self.router.get_active_app(dev_id)
                return {"success": True, "active_app": res}

            elif name == "list_devices":
                devices = self.registry.list_devices()
                return {"success": True, "devices": [d.name for d in devices]}

            else:
                return {"success": False, "error": f"Unknown tool: '{name}'"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Main Run Loop ────────────────────────────────────────────────

    def process_message(
        self,
        user_message: str,
        target_device: str = "mac-primary",
        on_action_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        Process a user command or conversational message.
        If Groq API key is configured, uses full LLM tool-calling loop.
        If no API key is configured, uses intelligent direct intent fallback.
        """
        self.api_key = self.load_api_key()

        # If no API key, use direct NLP fallback
        if not self.api_key:
            return self._fallback_direct_nlp(user_message, target_device, on_action_callback)

        # Full Groq API Tool-Calling Flow
        self.conversation_history.append({"role": "user", "content": user_message})

        max_iterations = 8
        for iteration in range(max_iterations):
            try:
                response = self._call_groq_api(self.conversation_history)
            except Exception as e:
                err_msg = str(e)
                if "401" in err_msg or "invalid_api_key" in err_msg.lower():
                    return f"❌ **Invalid Groq API Key**: Please click 🔑 in the top bar to update your API key.\n\n*(Error details: {err_msg})*"
                # Fallback to local parsing if Groq API hits rate limits or network issues
                if on_action_callback:
                    on_action_callback("info", "Groq API temporarily unavailable, using direct execution engine...")
                return self._fallback_direct_nlp(user_message, target_device, on_action_callback)

            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", [])

            # Add model's response to history
            self.conversation_history.append(message)

            # If model didn't call any tools, it's done talking to user
            if not tool_calls:
                return message.get("content", "Task completed.")

            # Execute tool calls requested by model
            for tool_call in tool_calls:
                func_name = tool_call.get("function", {}).get("name")
                args_str = tool_call.get("function", {}).get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}

                # Notify UI of action
                action_desc = f"Executing {func_name}..."
                if func_name == "open_app":
                    action_desc = f"Opening '{args.get('app_name')}'..."
                elif func_name == "type_text":
                    action_desc = f"Typing: \"{args.get('text')}\""
                elif func_name == "press_key":
                    action_desc = f"Pressing key: {args.get('key')}"
                elif func_name == "open_url":
                    action_desc = f"Navigating to {args.get('url')}..."

                if on_action_callback:
                    on_action_callback(func_name, action_desc)

                tool_result = self.execute_tool(func_name, args, default_device=target_device)

                # Return result to model conversation
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "name": func_name,
                    "content": json.dumps(tool_result)
                })

        return "Completed all requested actions."

    # ── Groq HTTP Client (urllib) ────────────────────────────────────

    def _call_groq_api(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send JSON-RPC payload to Groq API via standard urllib."""
        payload = {
            "model": DEFAULT_MODEL,
            "messages": messages,
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
            "temperature": 0.2,
            "max_tokens": 1024
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            GROQ_API_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "computerUse-Agent/1.0"
            }
        )

        with urllib.request.urlopen(req, timeout=30.0) as resp:
            raw_body = resp.read().decode("utf-8")
            return json.loads(raw_body)

    # ── Fallback Direct NLP Parser (Zero-Key Mode) ───────────────────

    def _fallback_direct_nlp(
        self,
        text: str,
        target_device: str,
        on_action_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        Direct deterministic intent parser when no Groq API key is present.
        Ensures the chatbot always executes user tasks seamlessly out of the box!
        """
        lower = text.strip().lower()

        # 1. Open App (e.g. "open blender", "launch calculator", "open notes")
        open_match = re.search(r"^(?:please\s+)?(?:open|launch|start|run)\s+(?:the\s+)?([a-zA-Z0-9\s\.\-_]+)$", lower)
        if open_match and not ("http://" in lower or "https://" in lower or ".com" in lower):
            app_raw = open_match.group(1).strip()
            # Title case app name (e.g. 'blender' -> 'Blender')
            app_name = app_raw.capitalize() if len(app_raw) > 2 else app_raw.upper()
            if on_action_callback:
                on_action_callback("open_app", f"Opening {app_name} on {target_device}...")
            res = self.execute_tool("open_app", {"app_name": app_name}, target_device)
            if res.get("success"):
                return f"✅ Launched **{app_name}** on your {target_device}!\n\n*(💡 Tip: Add your Groq API key via the 🔑 button in the top bar to enable full multi-step reasoning.)*"
            else:
                return f"❌ Failed to launch {app_name}: {res.get('error')}"

        # 2. Open URL / Website
        url_match = re.search(r"(?:open|goto|browse|navigate to)\s+(https?://\S+|www\.\S+|\S+\.(?:com|org|net|io|edu|gov)\S*)", text, re.IGNORECASE)
        if url_match or lower.startswith("http://") or lower.startswith("https://"):
            url = url_match.group(1) if url_match else text.strip()
            if not url.startswith("http"):
                url = f"https://{url}"
            if on_action_callback:
                on_action_callback("open_url", f"Opening {url}...")
            res = self.execute_tool("open_url", {"url": url}, target_device)
            return f"✅ Opened [{url}]({url}) in your default browser!"

        # 3. Type text (e.g. "type Hello World" or "write Welcome to Python")
        type_match = re.search(r"^(?:please\s+)?(?:type|write|input)\s+(.+)$", text, re.IGNORECASE)
        if type_match:
            content = type_match.group(1).strip().strip('"\'')
            if on_action_callback:
                on_action_callback("type_text", f"Typing: \"{content}\"...")
            res = self.execute_tool("type_text", {"text": content}, target_device)
            if res.get("success"):
                return f"✅ Typed text into active window: *\"{content}\"*"
            return f"❌ Could not type text: {res.get('error')}"

        # 4. Press shortcut or key
        press_match = re.search(r"^(?:please\s+)?(?:press|hit)\s+(.+)$", lower)
        if press_match:
            key_spec = press_match.group(1).strip()
            parts = key_spec.split("+")
            key = parts[-1].strip()
            mods = [p.strip() for p in parts[:-1]]
            if on_action_callback:
                on_action_callback("press_key", f"Pressing key: {key_spec}...")
            res = self.execute_tool("press_key", {"key": key, "modifiers": mods}, target_device)
            return f"✅ Pressed key: `{key_spec}`"

        # 5. Take Screenshot
        if "screenshot" in lower or "screen" in lower or "capture" in lower:
            if on_action_callback:
                on_action_callback("screenshot", f"Capturing screenshot of {target_device}...")
            res = self.execute_tool("screenshot", {}, target_device)
            return f"📸 Captured screen from **{target_device}**!"

        # 6. Click
        click_match = re.search(r"click\s+(?:at\s+)?(\d+)[,\s]+(\d+)", lower)
        if click_match:
            x, y = int(click_match.group(1)), int(click_match.group(2))
            if on_action_callback:
                on_action_callback("click", f"Clicking at ({x}, {y})...")
            res = self.execute_tool("click", {"x": x, "y": y}, target_device)
            return f"🖱️ Clicked at coordinate `({x}, {y})`."

        # 7. Semantic button click (e.g. "click 'Done'", "click save")
        semantic_click = re.search(r"click\s+(?:on\s+)?(?:button\s+)?[\"']?([^\"'\n]+)[\"']?", text, re.IGNORECASE)
        if semantic_click:
            label = semantic_click.group(1).strip()
            if on_action_callback:
                on_action_callback("click_ui_element", f"Searching and clicking element: '{label}'...")
            res = self.execute_tool("click_ui_element", {"query": label}, target_device)
            if res.get("success"):
                return f"🖱️ Found and clicked UI element: **{label}**"

        # 8. Conversational / Help
        if any(w in lower for w in ["hi", "hello", "hey", "help", "who are you", "what can you do"]):
            return (
                "👋 **Hello! I'm your Computer Use Chatbot.**\n\n"
                "I can control your Mac and Android tablet directly! Try saying:\n"
                "• **\"Open Blender\"**\n"
                "• **\"Open Calculator\"**\n"
                "• **\"Open Notes and write hello\"**\n"
                "• **\"Go to youtube.com\"**\n"
                "• **\"Take a screenshot\"**\n\n"
                "🔑 *For full autonomous reasoning across complex tasks, click the 🔑 button in the top bar to set your Groq API key!*"
            )

        # Default fallback: try to launch as an app or inform user
        return (
            f"I understood: *\"{text}\"*\n\n"
            f"To execute this command:\n"
            f"• Say **\"Open <app>\"** to launch an application.\n"
            f"• Say **\"Type <text>\"** to type into the focused app.\n"
            f"• Click the **🔑 Groq Key** button in the header so I can autonomously interpret any open-ended command with AI!"
        )
