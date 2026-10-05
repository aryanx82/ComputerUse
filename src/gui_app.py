"""
computerUse Desktop Application — Autonomous Chatbot Assistant
A modern chatbot interface for controlling Mac and Android devices using natural language,
powered by Groq AI (Llama 3.3 70B) with tool-calling and local direct execution fallback.
"""

import sys
import os
import time
import json
import base64
import io
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from src.registry import DeviceRegistry
from src.router import ToolRouter
from src.safety.guardrails import guardrails
from src.agent.groq_agent import GroqAgent


class ChatbotApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("computerUse — AI Chatbot Assistant")
        self.geometry("620x820")
        self.minsize(520, 680)

        # Dark theme base
        self.bg_main = "#11111b"
        self.bg_header = "#181825"
        self.bg_chat = "#181825"
        self.bg_card = "#1e1e2e"
        self.bg_user_bubble = "#3b82f6"
        self.bg_ai_bubble = "#252538"
        self.bg_tool_pill = "#313244"
        self.text_light = "#f8fafc"
        self.text_dim = "#94a3b8"
        self.accent_blue = "#89b4fa"
        self.accent_green = "#a6e3a1"
        self.accent_red = "#f38ba8"
        self.accent_purple = "#cba6f7"

        self.configure(bg=self.bg_main)

        # Lift window to front on launch
        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(self.attributes, '-topmost', False)
        self.focus_force()

        # Backend components
        self.registry = DeviceRegistry()
        self.router = ToolRouter(self.registry)
        self.guardrails = guardrails
        self.agent = GroqAgent(self.router, self.registry)

        self._is_busy = False
        self._preview_refs = []  # Retain photo images to avoid GC

        self._build_ui()
        self._refresh_devices()
        self._send_welcome_message()

    # ── UI Construction ──────────────────────────────────────────────

    def _build_ui(self):
        # ── 1. Top Header Bar ────────────────────────────────────────
        header = tk.Frame(self, bg=self.bg_header, height=65, padx=16, pady=10)
        header.pack(fill=tk.X)

        title_box = tk.Frame(header, bg=self.bg_header)
        title_box.pack(side=tk.LEFT, fill=tk.Y)

        title_lbl = tk.Label(
            title_box,
            text="🤖 computerUse",
            font=("Helvetica", 17, "bold"),
            fg=self.text_light,
            bg=self.bg_header
        )
        title_lbl.pack(anchor="w")

        self.status_sub_lbl = tk.Label(
            title_box,
            text="● Online • Ready to control Mac & Android",
            font=("Helvetica", 9),
            fg=self.accent_green,
            bg=self.bg_header
        )
        self.status_sub_lbl.pack(anchor="w")

        # Header Right Action Buttons
        btn_box = tk.Frame(header, bg=self.bg_header)
        btn_box.pack(side=tk.RIGHT, fill=tk.Y, pady=2)

        # Target Device Selector
        self.device_var = tk.StringVar(value="mac-primary")
        self.device_cb = ttk.Combobox(
            btn_box,
            textvariable=self.device_var,
            state="readonly",
            width=16,
            font=("Helvetica", 10)
        )
        self.device_cb.pack(side=tk.LEFT, padx=(0, 6), ipady=2)

        # Groq API Key Config Button
        key_btn = tk.Button(
            btn_box,
            text="🔑 Groq Key",
            font=("Helvetica", 9, "bold"),
            bg="#313244",
            fg=self.accent_purple,
            activebackground="#45475a",
            relief=tk.FLAT,
            command=self._show_api_key_dialog,
            padx=8,
            pady=3,
            cursor="pointinghand"
        )
        key_btn.pack(side=tk.LEFT, padx=(0, 4))

        # Clear Chat Button
        clear_btn = tk.Button(
            btn_box,
            text="🗑️",
            font=("Helvetica", 10),
            bg="#313244",
            fg=self.text_dim,
            activebackground="#45475a",
            relief=tk.FLAT,
            command=self._clear_chat,
            padx=6,
            pady=2,
            cursor="pointinghand"
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 4))

        # Emergency Stop Button
        self.stop_btn = tk.Button(
            btn_box,
            text="🛑 Stop",
            font=("Helvetica", 9, "bold"),
            bg="#f38ba8",
            fg="#11111b",
            activebackground="#eba0ac",
            relief=tk.FLAT,
            command=self._toggle_emergency_stop,
            padx=8,
            pady=3,
            cursor="pointinghand"
        )
        self.stop_btn.pack(side=tk.LEFT)

        # ── 2. Chat Conversation Canvas (Scrollable) ─────────────────
        chat_container = tk.Frame(self, bg=self.bg_chat)
        chat_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            chat_container,
            bg=self.bg_chat,
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.scrollbar = ttk.Scrollbar(
            chat_container,
            orient="vertical",
            command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_chat)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        # Make scrollable frame match canvas width
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # ── 3. Suggestion Chips Bar ──────────────────────────────────
        chips_frame = tk.Frame(self, bg=self.bg_main, padx=14, pady=6)
        chips_frame.pack(fill=tk.X)

        chips = [
            ("🎨 Open Blender", "Open Blender"),
            ("🧮 Open Calculator", "Open Calculator"),
            ("📝 Open Notes", "Open Notes"),
            ("🌐 Open Google", "Open https://google.com"),
            ("📸 Take Screenshot", "Take a screenshot of my screen"),
            ("📱 Wakeup Tablet", "Wakeup Android tablet"),
        ]

        for label, prompt in chips:
            chip_btn = tk.Button(
                chips_frame,
                text=label,
                font=("Helvetica", 9),
                bg=self.bg_card,
                fg=self.text_dim,
                activebackground="#313244",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                command=lambda p=prompt: self._submit_chip_prompt(p),
                padx=8,
                pady=2,
                cursor="pointinghand"
            )
            chip_btn.pack(side=tk.LEFT, padx=3)

        # ── 4. Message Input Bar ─────────────────────────────────────
        input_container = tk.Frame(self, bg=self.bg_main, padx=14, pady=10)
        input_container.pack(fill=tk.X)

        input_box = tk.Frame(
            input_container,
            bg=self.bg_card,
            padx=10,
            pady=6,
            highlightthickness=1,
            highlightbackground="#313244",
            highlightcolor=self.accent_blue
        )
        input_box.pack(fill=tk.X)

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            input_box,
            textvariable=self.entry_var,
            font=("Helvetica", 12),
            bg=self.bg_card,
            fg=self.text_light,
            insertbackground="#ffffff",
            relief=tk.FLAT
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self.entry.bind("<Return>", lambda e: self._on_send_click())
        self.entry.focus_set()

        self.send_btn = tk.Button(
            input_box,
            text="➤ Send",
            font=("Helvetica", 10, "bold"),
            bg=self.accent_blue,
            fg="#11111b",
            activebackground="#b4befe",
            relief=tk.FLAT,
            command=self._on_send_click,
            padx=14,
            pady=4,
            cursor="pointinghand"
        )
        self.send_btn.pack(side=tk.RIGHT, padx=(8, 0))

    # ── Chat Bubbles & Visual Elements ───────────────────────────────

    def _add_user_bubble(self, message: str):
        row = tk.Frame(self.scrollable_frame, bg=self.bg_chat, padx=12, pady=6)
        row.pack(fill=tk.X, anchor="e")

        bubble_container = tk.Frame(row, bg=self.bg_chat)
        bubble_container.pack(side=tk.RIGHT, anchor="e")

        header = tk.Label(
            bubble_container,
            text="You",
            font=("Helvetica", 8, "bold"),
            fg=self.text_dim,
            bg=self.bg_chat
        )
        header.pack(anchor="e", padx=4, pady=(0, 2))

        bubble = tk.Label(
            bubble_container,
            text=message,
            font=("Helvetica", 11),
            fg="#ffffff",
            bg=self.bg_user_bubble,
            wraplength=420,
            justify=tk.LEFT,
            padx=14,
            pady=9
        )
        bubble.pack(anchor="e")
        self._scroll_to_bottom()

    def _add_ai_bubble(self, message: str) -> tk.Label:
        row = tk.Frame(self.scrollable_frame, bg=self.bg_chat, padx=12, pady=6)
        row.pack(fill=tk.X, anchor="w")

        bubble_container = tk.Frame(row, bg=self.bg_chat)
        bubble_container.pack(side=tk.LEFT, anchor="w")

        header = tk.Label(
            bubble_container,
            text="🤖 Assistant",
            font=("Helvetica", 8, "bold"),
            fg=self.accent_blue,
            bg=self.bg_chat
        )
        header.pack(anchor="w", padx=4, pady=(0, 2))

        # Format markdown bold text slightly
        clean_text = message.replace("**", "")

        bubble = tk.Label(
            bubble_container,
            text=clean_text,
            font=("Helvetica", 11),
            fg=self.text_light,
            bg=self.bg_ai_bubble,
            wraplength=440,
            justify=tk.LEFT,
            padx=14,
            pady=9
        )
        bubble.pack(anchor="w")
        self._scroll_to_bottom()
        return bubble

    def _add_tool_pill(self, tool_name: str, desc: str):
        row = tk.Frame(self.scrollable_frame, bg=self.bg_chat, padx=16, pady=3)
        row.pack(fill=tk.X, anchor="w")

        icon = "⚡"
        if "open" in tool_name:
            icon = "🚀"
        elif "type" in tool_name:
            icon = "⌨️"
        elif "press" in tool_name:
            icon = "🔤"
        elif "click" in tool_name:
            icon = "🖱️"
        elif "screenshot" in tool_name:
            icon = "📸"

        pill = tk.Label(
            row,
            text=f"{icon}  {desc}",
            font=("Menlo", 9),
            fg=self.accent_amber,
            bg=self.bg_tool_pill,
            padx=10,
            pady=4
        )
        pill.pack(side=tk.LEFT)
        self._scroll_to_bottom()

    def _add_screenshot_preview(self, b64_img: str):
        """Render an inline screenshot thumbnail directly in the chat."""
        try:
            raw = base64.b64decode(b64_img)
            img = Image.open(io.BytesIO(raw))
            img.thumbnail((380, 240), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self._preview_refs.append(tk_img)

            row = tk.Frame(self.scrollable_frame, bg=self.bg_chat, padx=16, pady=4)
            row.pack(fill=tk.X, anchor="w")

            preview_lbl = tk.Label(
                row,
                image=tk_img,
                bg="#11111b",
                highlightthickness=1,
                highlightbackground="#45475a"
            )
            preview_lbl.pack(side=tk.LEFT)
            self._scroll_to_bottom()
        except Exception:
            pass

    def _scroll_to_bottom(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta)), "units")

    # ── Sending & Processing Messages ────────────────────────────────

    def _submit_chip_prompt(self, prompt: str):
        self.entry_var.set(prompt)
        self._on_send_click()

    def _on_send_click(self):
        msg = self.entry_var.get().strip()
        if not msg or self._is_busy:
            return

        self.entry_var.set("")
        self._add_user_bubble(msg)

        target_dev = self.device_var.get()
        self._set_busy(True)

        def _worker():
            def _action_cb(tool_name: str, desc: str):
                self.after(0, lambda: self._add_tool_pill(tool_name, desc))

            try:
                reply = self.agent.process_message(
                    user_message=msg,
                    target_device=target_dev,
                    on_action_callback=_action_cb
                )
                self.after(0, lambda: self._on_agent_reply(reply))
            except Exception as e:
                self.after(0, lambda: self._on_agent_reply(f"❌ Error: {str(e)}"))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_agent_reply(self, reply: str):
        self._add_ai_bubble(reply)

    def _set_busy(self, is_busy: bool):
        self._is_busy = is_busy
        if is_busy:
            self.send_btn.config(state=tk.DISABLED, text="Thinking...")
            self.status_sub_lbl.config(text="● Executing instructions on device...", fg=self.accent_amber)
        else:
            self.send_btn.config(state=tk.NORMAL, text="➤ Send")
            self.status_sub_lbl.config(text="● Online • Ready to control Mac & Android", fg=self.accent_green)

    def _send_welcome_message(self):
        has_key = bool(self.agent.api_key)
        key_note = (
            "🔑 **Groq API Key**: Active (Llama 3.3 70B enabled)"
            if has_key else
            "💡 **Direct Execution Mode**: Active (Click 🔑 to add a Groq API key for autonomous AI reasoning)"
        )

        welcome = (
            f"👋 **Hello! I'm your Computer Use Assistant.**\n\n"
            f"I have direct access to your Mac and connected Android devices.\n\n"
            f"**You can tell me to:**\n"
            f"• *Open Blender*\n"
            f"• *Open Calculator and do math*\n"
            f"• *Open Notes and write a message*\n"
            f"• *Go to google.com in browser*\n"
            f"• *Take a screenshot*\n\n"
            f"{key_note}"
        )
        self._add_ai_bubble(welcome)

    # ── Device & Settings Management ─────────────────────────────────

    def _refresh_devices(self):
        self.registry.discover_devices()
        devices = self.registry.list_devices()
        dev_ids = [d.id for d in devices]

        self.device_cb["values"] = dev_ids
        if dev_ids and self.device_var.get() not in dev_ids:
            self.device_var.set(dev_ids[0])

    def _show_api_key_dialog(self):
        win = tk.Toplevel(self)
        win.title("Configure Groq API Key")
        win.geometry("460x220")
        win.configure(bg=self.bg_header)
        win.transient(self)
        win.grab_set()

        tk.Label(
            win,
            text="🔑 Groq API Key Configuration",
            font=("Helvetica", 13, "bold"),
            fg=self.text_light,
            bg=self.bg_header
        ).pack(anchor="w", padx=16, pady=(16, 6))

        tk.Label(
            win,
            text="Enter your Groq key (gsk_...) to enable autonomous Llama 3.3 70B reasoning:",
            font=("Helvetica", 9),
            fg=self.text_dim,
            bg=self.bg_header,
            wraplength=420,
            justify=tk.LEFT
        ).pack(anchor="w", padx=16, pady=(0, 10))

        key_var = tk.StringVar(value=self.agent.api_key)
        entry = tk.Entry(
            win,
            textvariable=key_var,
            font=("Menlo", 11),
            bg=self.bg_card,
            fg="#ffffff",
            show="•",
            insertbackground="#ffffff",
            relief=tk.FLAT
        )
        entry.pack(fill=tk.X, padx=16, ipady=4)
        entry.focus_set()

        btn_row = tk.Frame(win, bg=self.bg_header)
        btn_row.pack(fill=tk.X, padx=16, pady=16)

        def _save():
            k = key_var.get().strip()
            self.agent.save_api_key(k)
            self.agent.api_key = k
            messagebox.showinfo("Saved", "Groq API key updated successfully!", parent=win)
            win.destroy()

        save_btn = tk.Button(
            btn_row,
            text="Save Key",
            font=("Helvetica", 10, "bold"),
            bg=self.accent_green,
            fg="#11111b",
            relief=tk.FLAT,
            command=_save,
            padx=14,
            pady=4,
            cursor="pointinghand"
        )
        save_btn.pack(side=tk.RIGHT)

        cancel_btn = tk.Button(
            btn_row,
            text="Cancel",
            font=("Helvetica", 10),
            bg="#313244",
            fg=self.text_dim,
            relief=tk.FLAT,
            command=win.destroy,
            padx=10,
            pady=4,
            cursor="pointinghand"
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 8))

    def _toggle_emergency_stop(self):
        if self.guardrails.is_emergency_stopped():
            self.guardrails.set_emergency_stop(False)
            self.stop_btn.config(text="🛑 Stop", bg="#f38ba8")
            self.status_sub_lbl.config(text="● Online • Ready to control Mac & Android", fg=self.accent_green)
            messagebox.showinfo("Resumed", "Device control resumed successfully!")
        else:
            self.guardrails.set_emergency_stop(True)
            self.stop_btn.config(text="🟢 Resume", bg=self.accent_green)
            self.status_sub_lbl.config(text="🛑 EMERGENCY STOP ENGAGED", fg=self.accent_red)
            messagebox.showwarning("EMERGENCY STOP", "Emergency stop engaged! All synthetic input halted.")

    def _clear_chat(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self._send_welcome_message()


if __name__ == "__main__":
    app = ChatbotApp()
    app.mainloop()
