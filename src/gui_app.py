"""
computerUse Desktop Application — GUI Control Center with Direct Command Runner
Allows direct, AI-free control of Mac and Android devices through natural commands,
quick macros, visual screen previews, and safety controls.
"""

import sys
import os
import time
import json
import base64
import io
import re
import shlex
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
from src.safety.guardrails import guardrails, SafetyGuardrails


class ComputerUseApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("computerUse — Cross-Device Control Center")
        self.geometry("1060x800")
        self.minsize(940, 720)

        # Apply dark theme styling
        self.configure(bg="#181825")
        self._setup_styles()

        # Lift window to front
        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(self.attributes, '-topmost', False)
        self.focus_force()

        # Backend components
        self.registry = DeviceRegistry()
        self.router = ToolRouter(self.registry)
        self.guardrails = guardrails

        self._preview_image = None
        self._is_testing = False
        self._is_executing_command = False

        self._build_ui()
        self._refresh_device_list()
        self._update_safety_indicator()

        # Schedule periodic status check (every 5 seconds)
        self.after(5000, self._auto_poll)

    def _setup_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Colors (Catppuccin Macchiato palette)
        self.bg_dark = "#181825"
        self.panel_bg = "#1e1e2e"
        self.card_bg = "#313244"
        self.text_light = "#cdd6f4"
        self.text_dim = "#a6adc8"
        self.accent_blue = "#89b4fa"
        self.accent_green = "#a6e3a1"
        self.accent_red = "#f38ba8"
        self.accent_amber = "#f9e2af"
        self.accent_purple = "#cba6f7"

        self.style.configure(".", background=self.panel_bg, foreground=self.text_light, font=("Helvetica", 11))
        self.style.configure("TLabel", background=self.panel_bg, foreground=self.text_light)
        self.style.configure("Card.TFrame", background=self.panel_bg)

    def _build_ui(self):
        # ── Top App Bar ──────────────────────────────────────────────
        top_bar = tk.Frame(self, bg="#11111b", height=65, padx=20, pady=10)
        top_bar.pack(fill=tk.X)

        title_frame = tk.Frame(top_bar, bg="#11111b")
        title_frame.pack(side=tk.LEFT, fill=tk.Y)

        title_lbl = tk.Label(
            title_frame,
            text="🖥️  computerUse",
            font=("Helvetica", 18, "bold"),
            fg="#cdd6f4",
            bg="#11111b"
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            title_frame,
            text="Direct Command & Hardware Control Center (Mac & Android)",
            font=("Helvetica", 10),
            fg="#a6adc8",
            bg="#11111b"
        )
        subtitle_lbl.pack(anchor="w")

        # Daemon Status Badge
        self.status_badge = tk.Label(
            top_bar,
            text="● ENGINE ACTIVE",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_green,
            bg="#181825",
            padx=14,
            pady=6,
            relief=tk.FLAT
        )
        self.status_badge.pack(side=tk.RIGHT, pady=6)

        # ── Main Content Area ────────────────────────────────────────
        main_frame = tk.Frame(self, bg=self.bg_dark, padx=14, pady=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left Column (Command Bar, Quick Actions, Console)
        left_col = tk.Frame(main_frame, bg=self.bg_dark, width=540)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Right Column (Screen preview, Devices, Safety)
        right_col = tk.Frame(main_frame, bg=self.bg_dark, width=440)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_command_card(left_col)
        self._build_quick_actions_card(left_col)
        self._build_console_card(left_col)

        self._build_preview_card(right_col)
        self._build_devices_card(right_col)
        self._build_safety_card(right_col)

    # ── Command Bar Card ─────────────────────────────────────────────

    def _build_command_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  ⚡ Direct Command Runner (No AI Needed)  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=12,
            pady=10
        )
        card.pack(fill=tk.X, pady=(0, 10))

        row1 = tk.Frame(card, bg=self.panel_bg)
        row1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row1, text="Target Device:", font=("Helvetica", 10, "bold"), bg=self.panel_bg).pack(side=tk.LEFT, padx=(0, 6))

        self.cmd_device_var = tk.StringVar(value="mac-primary")
        self.cmd_device_cb = ttk.Combobox(
            row1,
            textvariable=self.cmd_device_var,
            state="readonly",
            width=22
        )
        self.cmd_device_cb.pack(side=tk.LEFT, padx=(0, 10))
        self.cmd_device_cb.bind("<<ComboboxSelected>>", self._on_cmd_device_change)

        help_lbl = tk.Label(
            row1,
            text="Commands: open, type, click, press, url, scroll",
            font=("Helvetica", 9),
            fg=self.text_dim,
            bg=self.panel_bg
        )
        help_lbl.pack(side=tk.RIGHT)

        # Input Entry + Run Button
        row2 = tk.Frame(card, bg=self.panel_bg)
        row2.pack(fill=tk.X)

        self.cmd_entry = tk.Entry(
            row2,
            font=("Menlo", 12),
            bg=self.card_bg,
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#45475a",
            highlightcolor=self.accent_blue
        )
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=6)
        self.cmd_entry.bind("<Return>", lambda e: self._execute_command_from_entry())

        self.run_btn = tk.Button(
            row2,
            text="▶  Execute",
            font=("Helvetica", 11, "bold"),
            bg=self.accent_blue,
            fg="#11111b",
            activebackground="#b4befe",
            relief=tk.FLAT,
            command=self._execute_command_from_entry,
            padx=16,
            pady=4,
            cursor="pointinghand"
        )
        self.run_btn.pack(side=tk.RIGHT)

    # ── Quick Actions Card ───────────────────────────────────────────

    def _build_quick_actions_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  🎯 1-Click Direct Workflows  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_purple,
            bg=self.panel_bg,
            padx=10,
            pady=8
        )
        card.pack(fill=tk.X, pady=(0, 10))

        btn_grid = tk.Frame(card, bg=self.panel_bg)
        btn_grid.pack(fill=tk.X)

        # Row 1 of macros
        b1 = tk.Button(
            btn_grid,
            text="🧮 Open Calculator",
            font=("Helvetica", 10),
            bg=self.card_bg,
            fg=self.text_light,
            relief=tk.FLAT,
            command=lambda: self._run_custom_command("open Calculator"),
            cursor="pointinghand"
        )
        b1.grid(row=0, column=0, sticky="ew", padx=4, pady=3)

        b2 = tk.Button(
            btn_grid,
            text="📝 Open TextEdit & Type",
            font=("Helvetica", 10),
            bg=self.card_bg,
            fg=self.text_light,
            relief=tk.FLAT,
            command=self._macro_textedit_hello,
            cursor="pointinghand"
        )
        b2.grid(row=0, column=1, sticky="ew", padx=4, pady=3)

        b3 = tk.Button(
            btn_grid,
            text="🌐 Open Google in Browser",
            font=("Helvetica", 10),
            bg=self.card_bg,
            fg=self.text_light,
            relief=tk.FLAT,
            command=lambda: self._run_custom_command("open https://google.com"),
            cursor="pointinghand"
        )
        b3.grid(row=0, column=2, sticky="ew", padx=4, pady=3)

        # Row 2 of macros
        b4 = tk.Button(
            btn_grid,
            text="📱 Wakeup Tablet",
            font=("Helvetica", 10),
            bg=self.card_bg,
            fg=self.text_light,
            relief=tk.FLAT,
            command=lambda: self._run_custom_command("press wakeup", override_device="android-primary"),
            cursor="pointinghand"
        )
        b4.grid(row=1, column=0, sticky="ew", padx=4, pady=3)

        b5 = tk.Button(
            btn_grid,
            text="📱 Tablet Home Screen",
            font=("Helvetica", 10),
            bg=self.card_bg,
            fg=self.text_light,
            relief=tk.FLAT,
            command=lambda: self._run_custom_command("press home", override_device="android-primary"),
            cursor="pointinghand"
        )
        b5.grid(row=1, column=1, sticky="ew", padx=4, pady=3)

        b6 = tk.Button(
            btn_grid,
            text="📸 Capture Screen",
            font=("Helvetica", 10),
            bg=self.card_bg,
            fg=self.text_light,
            relief=tk.FLAT,
            command=self._capture_preview,
            cursor="pointinghand"
        )
        b6.grid(row=1, column=2, sticky="ew", padx=4, pady=3)

        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)
        btn_grid.columnconfigure(2, weight=1)

    # ── Console Output Card ──────────────────────────────────────────

    def _build_console_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  📟 Execution Console & Log  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=10,
            pady=8
        )
        card.pack(fill=tk.BOTH, expand=True)

        self.console_text = tk.Text(
            card,
            bg="#11111b",
            fg="#a6adc8",
            insertbackground="#ffffff",
            font=("Menlo", 10),
            relief=tk.FLAT,
            highlightthickness=0,
            wrap=tk.WORD,
            padx=8,
            pady=8
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)

        # Tags for colored console text
        self.console_text.tag_configure("cmd", foreground=self.accent_blue, font=("Menlo", 10, "bold"))
        self.console_text.tag_configure("success", foreground=self.accent_green)
        self.console_text.tag_configure("error", foreground=self.accent_red, font=("Menlo", 10, "bold"))
        self.console_text.tag_configure("info", foreground="#f5c2e7")

        self._log("System initialized. Native daemon and hardware adapters ready.", tag="success")
        self._log("Type any command above or click a workflow button to test!", tag="info")

    # ── Right Column: Preview, Devices, Safety ───────────────────────

    def _build_preview_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  📸 Live Screen Preview  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=10,
            pady=8
        )
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        top_row = tk.Frame(card, bg=self.panel_bg)
        top_row.pack(fill=tk.X, pady=(0, 6))

        snap_btn = tk.Button(
            top_row,
            text="🔄 Refresh Screen",
            font=("Helvetica", 10, "bold"),
            bg="#45475a",
            fg="#ffffff",
            relief=tk.FLAT,
            command=self._capture_preview,
            cursor="pointinghand"
        )
        snap_btn.pack(side=tk.LEFT)

        self.preview_meta_lbl = tk.Label(
            top_row,
            text="",
            font=("Helvetica", 9),
            fg=self.text_dim,
            bg=self.panel_bg
        )
        self.preview_meta_lbl.pack(side=tk.RIGHT)

        self.preview_canvas = tk.Canvas(
            card,
            bg="#11111b",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#45475a"
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

    def _build_devices_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  📱 Connected Devices  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=10,
            pady=8
        )
        card.pack(fill=tk.X, pady=(0, 10))

        self.device_listbox = tk.Listbox(
            card,
            bg=self.card_bg,
            fg=self.text_light,
            selectbackground=self.accent_blue,
            selectforeground="#11111b",
            font=("Helvetica", 10),
            height=3,
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.device_listbox.pack(fill=tk.X, pady=(2, 6))

        d_row = tk.Frame(card, bg=self.panel_bg)
        d_row.pack(fill=tk.X)

        refresh_btn = tk.Button(
            d_row,
            text="🔄 Scan Devices",
            font=("Helvetica", 9),
            bg="#45475a",
            fg="#ffffff",
            relief=tk.FLAT,
            command=self._refresh_device_list,
            cursor="pointinghand"
        )
        refresh_btn.pack(side=tk.LEFT)

        self.device_count_lbl = tk.Label(
            d_row,
            text="0 devices",
            font=("Helvetica", 9),
            fg=self.text_dim,
            bg=self.panel_bg
        )
        self.device_count_lbl.pack(side=tk.RIGHT)

    def _build_safety_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  🛡️ Emergency Kill-Switch  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=10,
            pady=8
        )
        card.pack(fill=tk.X)

        self.emergency_btn = tk.Button(
            card,
            text="🛑  ENGAGE EMERGENCY STOP",
            font=("Helvetica", 10, "bold"),
            bg="#f38ba8",
            fg="#11111b",
            activebackground="#eba0ac",
            relief=tk.FLAT,
            command=self._toggle_emergency_stop,
            pady=5,
            cursor="pointinghand"
        )
        self.emergency_btn.pack(fill=tk.X)

    # ── Console Logger ───────────────────────────────────────────────

    def _log(self, message: str, tag: str = None):
        t_str = time.strftime("[%H:%M:%S] ")
        self.console_text.insert(tk.END, t_str)
        if tag:
            self.console_text.insert(tk.END, message + "\n", tag)
        else:
            self.console_text.insert(tk.END, message + "\n")
        self.console_text.see(tk.END)

    # ── Command Execution Logic ──────────────────────────────────────

    def _execute_command_from_entry(self):
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
        self.cmd_entry.delete(0, tk.END)
        self._run_custom_command(cmd)

    def _run_custom_command(self, cmd_text: str, override_device: str = None):
        if self._is_executing_command:
            self._log("⚠️ Another command is currently executing, please wait...", tag="error")
            return

        target_dev = override_device or self.cmd_device_var.get()
        self._log(f"> {cmd_text}  (on {target_dev})", tag="cmd")

        self._is_executing_command = True
        self.run_btn.config(state=tk.DISABLED, text="Running...")

        def _worker():
            try:
                success, msg = self._parse_and_run(cmd_text, target_dev)
                if success:
                    self.after(0, lambda: self._log(f"✅ {msg}", tag="success"))
                else:
                    self.after(0, lambda: self._log(f"❌ {msg}", tag="error"))
            except Exception as e:
                self.after(0, lambda: self._log(f"❌ Error: {str(e)}", tag="error"))
            finally:
                self.after(0, self._finish_command_execution)
                # Auto refresh preview after command completes
                time.sleep(0.3)
                self.after(0, self._capture_preview)

        threading.Thread(target=_worker, daemon=True).start()

    def _finish_command_execution(self):
        self._is_executing_command = False
        self.run_btn.config(state=tk.NORMAL, text="▶  Execute")

    def _parse_and_run(self, cmd: str, dev_id: str) -> (bool, str):
        """
        Parses human-friendly commands and maps them directly to ToolRouter actions.
        Supported commands:
          open <app> / launch <app>
          open <url> (e.g. open https://...)
          type <text>
          click <x> <y>
          click "<label>" (semantic click)
          press <key> [modifiers]
          scroll [up/down] [amount]
          screenshot
          tree
        """
        parts = cmd.strip().split()
        if not parts:
            return True, "Empty command"

        verb = parts[0].lower()
        rest = cmd[len(parts[0]):].strip()

        # 1. Open URL
        if verb in ("open", "launch", "goto") and (rest.startswith("http://") or rest.startswith("https://") or rest.startswith("www.")):
            url = rest if rest.startswith("http") else f"https://{rest}"
            res = self.router.open_url(dev_id, url)
            return True, f"Opened URL: {url}"

        # 2. Open Application
        if verb in ("open", "launch", "app"):
            app_name = rest
            if not app_name:
                return False, "Usage: open <Application Name>"
            res = self.router.open_app(dev_id, app_name)
            return True, f"Launched '{app_name}' on {dev_id}"

        # 3. Type Text
        if verb in ("type", "write", "input"):
            text = rest
            if not text:
                return False, "Usage: type <text to type>"
            res = self.router.type_text(dev_id, text)
            if res.success:
                return True, f"Typed text: '{text}'"
            return False, f"Failed to type: {res.error}"

        # 4. Press Key / Shortcut
        if verb in ("press", "key", "shortcut"):
            # Syntax: press enter, press cmd+c, press home, press space
            tokens = rest.split("+")
            if len(tokens) == 1:
                key = tokens[0].strip()
                res = self.router.press_key(dev_id, key=key)
            else:
                key = tokens[-1].strip()
                modifiers = [t.strip() for t in tokens[:-1]]
                res = self.router.press_key(dev_id, key=key, modifiers=modifiers)

            if res.success:
                return True, f"Pressed key '{rest}'"
            return False, f"Keypress failed: {res.error}"

        # 5. Click
        if verb in ("click", "tap"):
            # Check if coordinates: click 500 300
            coord_match = re.match(r"^(\d+)\s+(\d+)$", rest)
            if coord_match:
                x = int(coord_match.group(1))
                y = int(coord_match.group(2))
                res = self.router.click(dev_id, x=x, y=y)
                if res.success:
                    return True, f"Clicked at ({x}, {y})"
                return False, f"Click failed: {res.error}"

            # Check if semantic element click: click "Submit" or click Submit
            label = rest.strip('"\'')
            if label:
                res = self.router.click_ui_element(dev_id, query=label)
                if res.success:
                    return True, f"Clicked UI element matching '{label}'"
                return False, f"Element click failed: {res.error}"

            return False, "Usage: click <x> <y>  OR  click '<element label>'"

        # 6. Scroll
        if verb in ("scroll", "swipe"):
            direction = rest.lower().strip()
            delta_y = -100  # scroll down by default
            if "up" in direction:
                delta_y = 100
            elif "down" in direction:
                delta_y = -100

            res = self.router.scroll(dev_id, delta_y=delta_y)
            if res.success:
                return True, f"Scrolled {direction or 'down'}"
            return False, f"Scroll failed: {res.error}"

        # 7. Screenshot
        if verb in ("screenshot", "snap", "capture"):
            shot = self.router.screenshot(dev_id, scale=0.5)
            return True, f"Captured screen: {shot.width}x{shot.height}"

        # 8. UI Tree Inspection
        if verb in ("tree", "ui", "inspect"):
            tree = self.router.get_ui_tree(dev_id, max_depth=3)
            return True, f"Inspected UI tree for app: '{tree.get('app_name', 'Unknown')}'"

        return False, f"Unknown command: '{cmd}'. Try: open, type, press, click, scroll, screenshot"

    # ── Macros ───────────────────────────────────────────────────────

    def _macro_textedit_hello(self):
        """Macro that opens TextEdit, waits for launch, and types a welcome message."""
        def _flow():
            self._log("Executing macro: Open TextEdit & Type Message...", tag="cmd")
            self.router.open_app("mac-primary", "TextEdit")
            time.sleep(1.2)
            # Create a new document with Cmd+N
            self.router.press_key("mac-primary", key="n", modifiers=["cmd"])
            time.sleep(0.5)
            # Type message
            msg = "Hello! The Computer Use Engine is fully working on your Mac without AI."
            self.router.type_text("mac-primary", text=msg)
            self._log("✅ TextEdit opened and message typed successfully!", tag="success")
            time.sleep(0.3)
            self.after(0, self._capture_preview)

        threading.Thread(target=_flow, daemon=True).start()

    # ── Device & Preview Management ──────────────────────────────────

    def _refresh_device_list(self):
        self.registry.discover_devices()
        devices = self.registry.list_devices()

        self.device_listbox.delete(0, tk.END)
        device_ids = []

        for d in devices:
            status_symbol = "🟢" if d.status.is_connected else "🔴"
            display_text = f"{status_symbol}  [{d.platform.upper()}]  {d.name}  ({d.id})"
            self.device_listbox.insert(tk.END, display_text)
            device_ids.append(d.id)

        self.device_count_lbl.config(text=f"{len(devices)} device(s) online")
        self.cmd_device_cb["values"] = device_ids
        if device_ids and self.cmd_device_var.get() not in device_ids:
            self.cmd_device_var.set(device_ids[0])

    def _on_cmd_device_change(self, event):
        self._capture_preview()

    def _capture_preview(self):
        dev_id = self.cmd_device_var.get()
        if not dev_id:
            return

        self.preview_meta_lbl.config(text="Capturing...")

        def _worker():
            t0 = time.time()
            try:
                shot = self.router.screenshot(dev_id, scale=0.5, format="jpeg")
                dt = (time.time() - t0) * 1000.0

                raw_bytes = base64.b64decode(shot.image_base64)
                img = Image.open(io.BytesIO(raw_bytes))

                canvas_w = self.preview_canvas.winfo_width() or 400
                canvas_h = self.preview_canvas.winfo_height() or 260

                img.thumbnail((canvas_w - 10, canvas_h - 10), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)

                self.after(0, lambda: self._display_preview(tk_img, shot.width, shot.height, dt))
            except Exception as e:
                self.after(0, lambda: self.preview_meta_lbl.config(text=f"Error: {str(e)[:30]}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _display_preview(self, tk_img, orig_w, orig_h, latency_ms):
        self._preview_image = tk_img
        self.preview_canvas.delete("all")
        canvas_w = self.preview_canvas.winfo_width()
        canvas_h = self.preview_canvas.winfo_height()

        self.preview_canvas.create_image(
            canvas_w // 2,
            canvas_h // 2,
            image=tk_img,
            anchor=tk.CENTER
        )
        self.preview_meta_lbl.config(text=f"{orig_w}x{orig_h} • {latency_ms:.0f}ms")

    def _toggle_emergency_stop(self):
        if self.guardrails.is_emergency_stopped():
            self.guardrails.set_emergency_stop(False)
            messagebox.showinfo("Control Resumed", "Emergency stop lifted. Normal operation resumed.")
        else:
            self.guardrails.set_emergency_stop(True)
            messagebox.showwarning("EMERGENCY STOP", "Emergency stop ENGAGED! All tool operations are now frozen.")

        self._update_safety_indicator()

    def _update_safety_indicator(self):
        if self.guardrails.is_emergency_stopped():
            self.status_badge.config(
                text="🛑 EMERGENCY STOPPED",
                fg="#11111b",
                bg=self.accent_red
            )
            self.emergency_btn.config(
                text="🟢  RESUME DEVICE CONTROL",
                bg=self.accent_green,
                fg="#11111b"
            )
        else:
            self.status_badge.config(
                text="● ENGINE ACTIVE",
                fg=self.accent_green,
                bg="#181825"
            )
            self.emergency_btn.config(
                text="🛑  ENGAGE EMERGENCY STOP",
                bg=self.accent_red,
                fg="#11111b"
            )

    def _auto_poll(self):
        self._update_safety_indicator()
        self.after(5000, self._auto_poll)


if __name__ == "__main__":
    app = ComputerUseApp()
    app.mainloop()
