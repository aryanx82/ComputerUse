"""
Interactive CLI Test Client for Computer Use Tool (Milestones 1, 2, & 3)
Lets you manually test every capability across Mac and Android without an AI host.
"""

import sys
import base64
import json
from src.registry import DeviceRegistry
from src.router import ToolRouter

def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║        Computer Use Tool — Multi-Device Tester       ║")
    print("╚══════════════════════════════════════════════════════╝")
    
    registry = DeviceRegistry()
    router = ToolRouter(registry)
    
    devices = registry.list_devices()
    print("\nDiscovered devices:")
    for idx, d in enumerate(devices, 1):
        status_str = "🟢 Online" if d.status.is_connected else "🔴 Offline"
        print(f"  {idx}. [{d.platform.upper()}] {d.id} — {d.name} ({status_str})")
        
    current_device = devices[0].id if devices else "mac-primary"
    print(f"\n🎯 Currently selected target: [{current_device}]")

    print("\nAvailable Commands:")
    print("  0.  device      - Switch target device (mac-primary, android-primary, etc.)")
    print("  1.  screenshot  - Capture screen and save to disk")
    print("  2.  click       - Click / tap at (x, y) coordinates")
    print("  3.  type        - Type text")
    print("  4.  key         - Press a key or shortcut (return, home, back, wakeup, cmd+c)")
    print("  5.  scroll      - Scroll up or down at (x, y)")
    print("  6.  drag        - Drag from (x1, y1) to (x2, y2)")
    print("  7.  uitree      - Dump accessible UI element tree")
    print("  8.  activeapp   - Get frontmost application / package info")
    print("  9.  openapp     - Launch an application (e.g. Safari, settings, chrome)")
    print("  10. quit        - Exit this tester")

    while True:
        try:
            cmd = input(f"\n👉 [{current_device}] Enter command: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break
            
        if cmd in ("quit", "exit", "q", "10"):
            print("Bye!")
            break
            
        elif cmd in ("device", "switch", "0"):
            registry.refresh()
            devs = registry.list_devices()
            print("\nAvailable devices:")
            for i, d in enumerate(devs, 1):
                print(f"  {i}. {d.id} ({d.name}) [{d.platform}]")
            choice = input("  Select device ID or number: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(devs):
                current_device = devs[int(choice) - 1].id
            elif choice:
                current_device = choice
            print(f"  🎯 Target device switched to: {current_device}")

        elif cmd in ("screenshot", "1"):
            try:
                scale_input = input("  Scale factor (0.1 to 1.0, default 0.5): ").strip()
                scale = float(scale_input) if scale_input else 0.5
                print(f"  Capturing screenshot on {current_device}...")
                res = router.screenshot(current_device, scale=scale)
                filename = f"screenshot_{current_device}.jpg"
                with open(filename, "wb") as f:
                    f.write(base64.b64decode(res.image_base64))
                print(f"  ✅ Saved screenshot to {filename} ({res.width}x{res.height} px)")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        elif cmd in ("click", "tap", "2"):
            try:
                x = int(input("  X coordinate: ").strip())
                y = int(input("  Y coordinate: ").strip())
                btn = input("  Button (left/right, default left): ").strip().lower() or "left"
                res = router.click(current_device, x, y, button=btn)
                if res.success:
                    print(f"  ✅ Clicked/tapped at ({x}, {y}) on {current_device}")
                else:
                    print(f"  ❌ Click failed: {res.error}")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        elif cmd in ("type", "3"):
            try:
                text = input("  Enter text to type: ")
                res = router.type_text(current_device, text)
                if res.success:
                    print(f"  ✅ Typed '{text}' on {current_device}")
                else:
                    print(f"  ❌ Typing failed: {res.error}")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        elif cmd in ("key", "4"):
            try:
                raw_key = input("  Enter key or combo (e.g. 'home', 'back', 'wakeup', 'return', 'cmd+c'): ").strip()
                parts = [p.strip().lower() for p in raw_key.split("+")]
                key = parts[-1]
                modifiers = parts[:-1]
                res = router.press_key(current_device, key, modifiers=modifiers)
                if res.success:
                    print(f"  ✅ Pressed '{raw_key}' on {current_device}")
                else:
                    print(f"  ❌ Key press failed: {res.error}")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        elif cmd in ("scroll", "5"):
            try:
                x = int(input("  X coordinate (default 500): ") or 500)
                y = int(input("  Y coordinate (default 800): ") or 800)
                amount = int(input("  Scroll amount (negative=down/swipe-up, positive=up, default -200): ") or -200)
                res = router.scroll(current_device, x, y, delta_y=amount)
                if res.success:
                    print(f"  ✅ Scrolled deltaY={amount} at ({x}, {y}) on {current_device}")
                else:
                    print(f"  ❌ Scroll failed: {res.error}")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        elif cmd in ("drag", "6"):
            try:
                x1 = int(input("  From X: "))
                y1 = int(input("  From Y: "))
                x2 = int(input("  To X: "))
                y2 = int(input("  To Y: "))
                res = router.drag(current_device, x1, y1, x2, y2)
                if res.success:
                    print(f"  ✅ Dragged from ({x1}, {y1}) to ({x2}, {y2}) on {current_device}")
                else:
                    print(f"  ❌ Drag failed: {res.error}")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        elif cmd in ("uitree", "7"):
            try:
                print(f"  Reading accessibility UI tree from {current_device}...")
                tree = router.get_ui_tree(current_device, max_depth=3, max_children=8)
                print(json.dumps(tree, indent=2))
            except Exception as e:
                print(f"  ❌ Error: {e}")

        elif cmd in ("activeapp", "8"):
            try:
                app = router.get_active_app(current_device)
                print(f"  Active App on {current_device}: {json.dumps(app, indent=2)}")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        elif cmd in ("openapp", "9"):
            try:
                name = input("  Application name/package (e.g. Safari, Notes, settings, chrome): ").strip()
                res = router.open_app(current_device, name)
                print(f"  ✅ Open app result on {current_device}: {res}")
            except Exception as e:
                print(f"  ❌ Error: {e}")

        else:
            print("  Unknown command. Enter a command name or number from the list.")

if __name__ == "__main__":
    main()
