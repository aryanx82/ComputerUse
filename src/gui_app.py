"""
computerUse Desktop Application — GUI Control Center
Provides a graphical interface to view device status, inspect live screen previews,
toggle the emergency kill-switch, copy AI configurations, and manage the MCP server.
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

# Ensure project root is in python path
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from src.registry import DeviceRegistry
from src.router import ToolRouter
from src.safety.guardrails import guardrails, SafetyGuardrails


class ComputerUseApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("computerUse — Cross-Device AI Control Center")
        self.geometry("960x740")
        self.minsize(860, 680)

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

        # Colors
        self.bg_dark = "#181825"
        self.panel_bg = "#1e1e2e"
        self.card_bg = "#313244"
        self.text_light = "#cdd6f4"
        self.text_dim = "#a6adc8"
        self.accent_blue = "#89b4fa"
        self.accent_green = "#a6e3a1"
        self.accent_red = "#f38ba8"
        self.accent_amber = "#f9e2af"

        self.style.configure(".", background=self.panel_bg, foreground=self.text_light, font=("Helvetica", 11))
        self.style.configure("TLabel", background=self.panel_bg, foreground=self.text_light)
        self.style.configure("Card.TFrame", background=self.panel_bg)
        self.style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), foreground="#ffffff")
        self.style.configure("SubHeader.TLabel", font=("Helvetica", 11), foreground=self.text_dim)
        self.style.configure("Section.TLabel", font=("Helvetica", 12, "bold"), foreground=self.accent_blue)
        self.style.configure("Status.TLabel", font=("Helvetica", 10, "bold"))

    def _build_ui(self):
        # ── Top App Bar ──────────────────────────────────────────────
        top_bar = tk.Frame(self, bg="#11111b", height=70, padx=20, pady=12)
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
            text="Cross-Device AI Control Bridge (Mac & Android)",
            font=("Helvetica", 10),
            fg="#a6adc8",
            bg="#11111b"
        )
        subtitle_lbl.pack(anchor="w")

        # Daemon Status Badge
        self.status_badge = tk.Label(
            top_bar,
            text="● SYSTEM ACTIVE",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_green,
            bg="#181825",
            padx=14,
            pady=6,
            relief=tk.FLAT
        )
        self.status_badge.pack(side=tk.RIGHT, pady=6)

        # ── Main Content Area ────────────────────────────────────────
        main_frame = tk.Frame(self, bg=self.bg_dark, padx=16, pady=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left Column (Device list, Safety, Host configs)
        left_col = tk.Frame(main_frame, bg=self.bg_dark, width=420)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))

        # Right Column (Screen preview, Diagnostics)
        right_col = tk.Frame(main_frame, bg=self.bg_dark)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_devices_card(left_col)
        self._build_safety_card(left_col)
        self._build_ai_config_card(left_col)

        self._build_preview_card(right_col)
        self._build_diagnostics_card(right_col)

    def _build_devices_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  📱 Connected Hardware Devices  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=12,
            pady=10
        )
        card.pack(fill=tk.X, pady=(0, 12))

        self.device_listbox = tk.Listbox(
            card,
            bg=self.card_bg,
            fg=self.text_light,
            selectbackground=self.accent_blue,
            selectforeground="#11111b",
            font=("Helvetica", 11),
            height=4,
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.device_listbox.pack(fill=tk.X, pady=(4, 8))
        self.device_listbox.bind("<<ListboxSelect>>", self._on_device_selected)

        btn_row = tk.Frame(card, bg=self.panel_bg)
        btn_row.pack(fill=tk.X)

        refresh_btn = tk.Button(
            btn_row,
            text="🔄 Refresh Devices",
            font=("Helvetica", 10, "bold"),
            bg="#45475a",
            fg="#ffffff",
            activebackground="#585b70",
            relief=tk.FLAT,
            command=self._refresh_device_list,
            cursor="pointinghand"
        )
        refresh_btn.pack(side=tk.LEFT)

        self.device_count_lbl = tk.Label(
            btn_row,
            text="0 devices",
            font=("Helvetica", 10),
            fg=self.text_dim,
            bg=self.panel_bg
        )
        self.device_count_lbl.pack(side=tk.RIGHT)

    def _build_safety_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  🛡️ Safety Guardrails & Kill-Switch  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=12,
            pady=10
        )
        card.pack(fill=tk.X, pady=(0, 12))

        self.safety_status_lbl = tk.Label(
            card,
            text="Policy: Strict Mode (Destructive actions blocked)",
            font=("Helvetica", 10),
            fg=self.accent_green,
            bg=self.panel_bg
        )
        self.safety_status_lbl.pack(anchor="w", pady=(0, 8))

        # Emergency Stop / Resume Button
        self.emergency_btn = tk.Button(
            card,
            text="🛑  ENGAGE EMERGENCY STOP",
            font=("Helvetica", 11, "bold"),
            bg="#f38ba8",
            fg="#11111b",
            activebackground="#eba0ac",
            relief=tk.FLAT,
            command=self._toggle_emergency_stop,
            pady=6,
            cursor="pointinghand"
        )
        self.emergency_btn.pack(fill=tk.X, pady=(0, 8))

        log_btn = tk.Button(
            card,
            text="📄 View Security Audit Log",
            font=("Helvetica", 10),
            bg="#45475a",
            fg="#ffffff",
            activebackground="#585b70",
            relief=tk.FLAT,
            command=self._open_audit_log,
            cursor="pointinghand"
        )
        log_btn.pack(fill=tk.X)

    def _build_ai_config_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  🤖 Connect to AI Clients  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=12,
            pady=10
        )
        card.pack(fill=tk.X)

        desc_lbl = tk.Label(
            card,
            text="Copy turnkey JSON configurations into your AI host:",
            font=("Helvetica", 10),
            fg=self.text_dim,
            bg=self.panel_bg
        )
        desc_lbl.pack(anchor="w", pady=(0, 8))

        claude_btn = tk.Button(
            card,
            text="📋 Copy Claude Desktop Config",
            font=("Helvetica", 10, "bold"),
            bg="#313244",
            fg=self.accent_blue,
            activebackground="#45475a",
            relief=tk.FLAT,
            command=self._copy_claude_config,
            pady=5,
            cursor="pointinghand"
        )
        claude_btn.pack(fill=tk.X, pady=(0, 6))

        cursor_btn = tk.Button(
            card,
            text="📋 Copy Cursor IDE Config",
            font=("Helvetica", 10, "bold"),
            bg="#313244",
            fg=self.accent_blue,
            activebackground="#45475a",
            relief=tk.FLAT,
            command=self._copy_cursor_config,
            pady=5,
            cursor="pointinghand"
        )
        cursor_btn.pack(fill=tk.X)

    def _build_preview_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  📸 Live Screen Preview  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=12,
            pady=10
        )
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        controls_row = tk.Frame(card, bg=self.panel_bg)
        controls_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(controls_row, text="Target Device:", font=("Helvetica", 10), bg=self.panel_bg).pack(side=tk.LEFT, padx=(0, 6))

        self.preview_device_var = tk.StringVar(value="mac-primary")
        self.preview_device_cb = ttk.Combobox(
            controls_row,
            textvariable=self.preview_device_var,
            state="readonly",
            width=22
        )
        self.preview_device_cb.pack(side=tk.LEFT, padx=(0, 10))

        snap_btn = tk.Button(
            controls_row,
            text="📷 Capture Screenshot",
            font=("Helvetica", 10, "bold"),
            bg=self.accent_blue,
            fg="#11111b",
            activebackground="#b4befe",
            relief=tk.FLAT,
            command=self._capture_preview,
            cursor="pointinghand"
        )
        snap_btn.pack(side=tk.LEFT)

        self.preview_meta_lbl = tk.Label(
            controls_row,
            text="",
            font=("Helvetica", 9),
            fg=self.text_dim,
            bg=self.panel_bg
        )
        self.preview_meta_lbl.pack(side=tk.RIGHT)

        # Canvas for image preview
        self.preview_canvas = tk.Canvas(
            card,
            bg="#11111b",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#45475a"
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

    def _build_diagnostics_card(self, parent):
        card = tk.LabelFrame(
            parent,
            text="  🧪 Health & Integration Diagnostics  ",
            font=("Helvetica", 11, "bold"),
            fg=self.accent_blue,
            bg=self.panel_bg,
            padx=12,
            pady=10
        )
        card.pack(fill=tk.X)

        test_row = tk.Frame(card, bg=self.panel_bg)
        test_row.pack(fill=tk.X)

        self.run_test_btn = tk.Button(
            test_row,
            text="⚡ Run Master Integration Test",
            font=("Helvetica", 10, "bold"),
            bg="#a6e3a1",
            fg="#11111b",
            activebackground="#94e2d5",
            relief=tk.FLAT,
            command=self._run_integration_tests,
            cursor="pointinghand"
        )
        self.run_test_btn.pack(side=tk.LEFT)

        self.test_status_lbl = tk.Label(
            test_row,
            text="Ready to verify all devices",
            font=("Helvetica", 10),
            fg=self.text_dim,
            bg=self.panel_bg
        )
        self.test_status_lbl.pack(side=tk.LEFT, padx=(12, 0))

    # ── Logic & Event Handlers ───────────────────────────────────────

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
        self.preview_device_cb["values"] = device_ids
        if device_ids and self.preview_device_var.get() not in device_ids:
            self.preview_device_var.set(device_ids[0])

    def _on_device_selected(self, event):
        selection = self.device_listbox.curselection()
        if selection:
            devices = self.registry.list_devices()
            if selection[0] < len(devices):
                dev = devices[selection[0]]
                self.preview_device_var.set(dev.id)

    def _capture_preview(self):
        dev_id = self.preview_device_var.get()
        if not dev_id:
            messagebox.showwarning("No Device", "Please select a device first.")
            return

        self.preview_meta_lbl.config(text="Capturing...")
        self.update()

        def _worker():
            t0 = time.time()
            try:
                shot = self.router.screenshot(dev_id, scale=0.5, format="jpeg")
                dt = (time.time() - t0) * 1000.0

                raw_bytes = base64.b64decode(shot.image_base64)
                img = Image.open(io.BytesIO(raw_bytes))

                # Scale to fit canvas
                canvas_w = self.preview_canvas.winfo_width() or 480
                canvas_h = self.preview_canvas.winfo_height() or 320

                img.thumbnail((canvas_w - 20, canvas_h - 20), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)

                self.after(0, lambda: self._display_preview(tk_img, shot.width, shot.height, dt))
            except Exception as e:
                self.after(0, lambda: self.preview_meta_lbl.config(text=f"Error: {str(e)[:35]}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _display_preview(self, tk_img, orig_w, orig_h, latency_ms):
        self._preview_image = tk_img  # Keep reference
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
            # Resume
            self.guardrails.set_emergency_stop(False)
            messagebox.showinfo("Control Resumed", "Emergency stop has been lifted. Normal operation resumed.")
        else:
            # Engage Stop
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
            self.safety_status_lbl.config(
                text="STATUS: ALL ACTIONS BLOCKED (Kill-Switch Active)",
                fg=self.accent_red
            )
        else:
            self.status_badge.config(
                text="● SYSTEM ACTIVE",
                fg=self.accent_green,
                bg="#181825"
            )
            self.emergency_btn.config(
                text="🛑  ENGAGE EMERGENCY STOP",
                bg=self.accent_red,
                fg="#11111b"
            )
            self.safety_status_lbl.config(
                text="Policy: Strict Mode (Destructive actions blocked)",
                fg=self.accent_green
            )

    def _open_audit_log(self):
        log_path = os.path.expanduser("~/.computer-use-tool/audit.log")
        if not os.path.exists(log_path):
            messagebox.showinfo("Audit Log", "No audit log records recorded yet.")
            return

        # Open in default macOS application
        subprocess.run(["open", log_path])

    def _copy_claude_config(self):
        cfg_path = os.path.join(SCRIPT_DIR, "config", "claude_desktop_config.json")
        try:
            with open(cfg_path, "r") as f:
                content = f.read()
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo(
                "Copied to Clipboard!",
                "Claude Desktop configuration JSON copied to clipboard!\n\n"
                "Paste it into:\n"
                "~/Library/Application Support/Claude/claude_desktop_config.json"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read config: {e}")

    def _copy_cursor_config(self):
        cfg_path = os.path.join(SCRIPT_DIR, "config", "cursor_mcp.json")
        try:
            with open(cfg_path, "r") as f:
                content = f.read()
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo(
                "Copied to Clipboard!",
                "Cursor MCP configuration JSON copied to clipboard!\n\n"
                "Add it in Cursor Settings → Features → MCP Servers."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read config: {e}")

    def _run_integration_tests(self):
        if self._is_testing:
            return

        self._is_testing = True
        self.run_test_btn.config(state=tk.DISABLED, text="Testing in progress...")
        self.test_status_lbl.config(text="Running Master Test Suite across all devices...", fg=self.accent_amber)

        def _test_worker():
            try:
                env = os.environ.copy()
                env["PYTHONPATH"] = SCRIPT_DIR
                res = subprocess.run(
                    [sys.executable, os.path.join(SCRIPT_DIR, "tests", "test_master_integration.py")],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=90
                )
                success = (res.returncode == 0)
                output = res.stdout if success else (res.stderr or res.stdout)
                self.after(0, lambda: self._on_test_finished(success, output))
            except Exception as e:
                self.after(0, lambda: self._on_test_finished(False, str(e)))

        threading.Thread(target=_test_worker, daemon=True).start()

    def _on_test_finished(self, success: bool, output: str):
        self._is_testing = False
        self.run_test_btn.config(state=tk.NORMAL, text="⚡ Run Master Integration Test")

        if success:
            self.test_status_lbl.config(text="✅ All Tests Passed! 0 Bugs Detected.", fg=self.accent_green)
            messagebox.showinfo("Test Suite Passed", "🎉 Master Integration Suite Passed with 100% success!\nAll devices and tools are fully operational.")
        else:
            self.test_status_lbl.config(text="❌ Test Failure Detected", fg=self.accent_red)
            messagebox.showerror("Test Failed", f"Master Test encountered an error:\n\n{output[:300]}")

    def _auto_poll(self):
        """Periodic background status refresher."""
        self._update_safety_indicator()
        self.after(5000, self._auto_poll)


if __name__ == "__main__":
    app = ComputerUseApp()
    app.mainloop()
