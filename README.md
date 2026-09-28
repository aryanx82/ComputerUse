# 🌐 Cross-Device Computer Use Tool (MCP Server)

A unified, production-grade Model Context Protocol (MCP) server that empowers external AIs (such as **Claude Desktop**, **Cursor IDE**, or any MCP-compatible agent) to observe and interact with your **Mac**, **Android tablet**, and **Android phone** simultaneously — exactly like a human user.

---

## 🌟 Capabilities Overview

| Capability | macOS (via Native Swift Daemon) | Android (via ADB Engine) |
| :--- | :--- | :--- |
| **Visual Observation** | Ultra-low latency screenshots via `ScreenCaptureKit` | Fast direct PNG streaming via `SurfaceFlinger` |
| **Touch / Mouse** | Single, double, and right click via `CGEvent` | Multi-touch taps, double taps via `/dev/input` |
| **Typing** | Full UTF-8 & Unicode typing via `CGEventKeyboardSetUnicodeString` | High-speed typing with safe shell escaping |
| **Key Shortcuts** | Physical keys & modifiers (`cmd+c`, `tab`, `enter`, etc.) | Android keys (`home`, `back`, `recents`, `wakeup`, etc.) |
| **Gestures & Motion** | Smooth pixel scrolling & drag gestures | Touch flick-scrolling & interpolated drag swipes |
| **Application Control** | Frontmost app detection & synchronous app launching | Active package/activity detection & app/URL intent launch |
| **Semantic UI Tree** | Full accessibility hierarchy via `AXUIElement` | UI Automator XML hierarchy & node parser |
| **Semantic Action** | Direct element clicking by accessibility label | Direct element clicking by text, description, or resource-id |
| **Safety & Control** | Strict destructive command guardrails & emergency kill-switch | Strict destructive command guardrails & emergency kill-switch |

---

## 🏗️ Architecture

```
                    ┌───────────────────────────────┐
                    │   External AI (MCP Client)    │
                    │   Claude Desktop / Cursor IDE │
                    └───────────────┬───────────────┘
                                    │ stdio (JSON-RPC)
                    ┌───────────────▼───────────────┐
                    │     MCP Server (Python)       │
                    │   src/server.py (17 Tools)    │
                    └───────┬───────────────┬───────┘
                            │               │
            ┌───────────────▼────────┐     ┌▼──────────────────────┐
            │ Safety & Audit Guard   │     │ Device Registry       │
            │ Rate Limiter & Logger  │     │ Dynamic Discovery     │
            └───────────────┬────────┘     └┬──────────────────────┘
                            │               │
           ┌────────────────▼───────────────▼────────────────┐
           │                  Tool Router                    │
           └──────────────┬───────────────────┬──────────────┘
                          │                   │
         Unix Domain Sock │ (0.5ms IPC)       │ ADB Protocol
         ~/.computer-use-tool/daemon.sock     │ (USB / Wi-Fi)
                          │                   │
             ┌────────────▼──────────┐    ┌───▼──────────────────┐
             │  macOS Native Daemon  │    │   Android Devices    │
             │   (Swift / Release)   │    │  (Samsung Tab, etc.) │
             │ ScreenCaptureKit, AX  │    │  SurfaceFlinger, AM  │
             └───────────────────────┘    └──────────────────────┘
```

---

## 🚀 Quick Start (Beginner Friendly)

### 1. Prerequisites
- **macOS 14.0+** (Sonoma or Sequoia)
- **Python 3.11+**
- **Xcode Command Line Tools**:
  ```bash
  xcode-select --install
  ```
- **Android Setup** (if controlling Android tablet or phone):
  - Enable **Developer Options** & **USB Debugging** on your Android device.
  - Connect your device via USB (or wireless ADB) and tap **"Always allow from this computer"**.
  - Verify with: `adb devices`

### 2. macOS Permissions (One-Time Setup)
macOS requires explicit user permissions to record the screen and send keystrokes:
1. Open **System Settings** → **Privacy & Security** → **Screen Recording**.
   - Enable your Terminal app (Terminal, iTerm2, or Cursor/VS Code).
2. Open **System Settings** → **Privacy & Security** → **Accessibility**.
   - Enable your Terminal app (Terminal, iTerm2, or Cursor/VS Code).

---

## 🎮 Running the Tool

Everything is managed seamlessly via the single `./run.sh` launcher:

```bash
# Check system status, running daemon, and connected devices
./run.sh --status

# Launch the interactive testing CLI
./run.sh --interactive

# Run the master automated test suite (all milestones)
./run.sh --test

# Start the MCP server for AI clients (stdio mode)
./run.sh --stdio
```

> **Automatic Self-Healing**: The Swift native daemon automatically compiles and starts in the background whenever an MCP tool is called. You never need to manage background processes manually.

---

## 🤖 Connecting to AI Clients

### Connecting to Claude Desktop
Edit your Claude Desktop configuration file:
`~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "computer-use": {
      "command": "/Users/aryan.yadav2024/.gemini/antigravity/scratch/computer-use-tool/run.sh",
      "args": ["--stdio"]
    }
  }
}
```

### Connecting to Cursor IDE
In Cursor, go to **Cursor Settings** → **Features** → **MCP Servers** → **Add New MCP Server**:
- **Name**: `computer-use`
- **Type**: `command`
- **Command**: `/Users/aryan.yadav2024/.gemini/antigravity/scratch/computer-use-tool/run.sh --stdio`

---

## 🛠️ Complete MCP Tool Reference (17 Tools)

### 1. Device Discovery & Inspection
- **`list_devices()`**: Discover all connected devices (macOS primary host, Android phones, tablets).
- **`get_device_info(device_id)`**: Inspect detailed hardware specifications, capabilities, and screen resolutions.
- **`get_active_app(device_id)`**: Retrieve the currently focused frontmost application or active Android package.

### 2. Observation & Semantic Perception
- **`screenshot(device_id, scale=1.0, format="jpeg")`**: Capture high-definition screen images with optional downscaling (e.g., `scale=0.5`) to optimize AI token usage.
- **`get_ui_tree(device_id, max_depth=8)`**: Export a normalized, cross-platform accessibility tree containing window titles, roles, interactive elements, and bounding boxes.
- **`find_ui_elements(device_id, query, role=None)`**: Search the UI tree for elements matching text, labels, or roles, returning their exact screen coordinates and click centers.

### 3. Mouse, Touch & Keyboard Interaction
- **`click(device_id, x, y, button="left", click_count=1, return_screenshot=False)`**: Perform single click, double click, or right click on macOS, or precise touch tap on Android.
- **`click_ui_element(device_id, query, role=None, return_screenshot=False)`**: **Direct Semantic Click** — searches the UI tree for a matching label/button and clicks its exact bounding center in one step.
- **`type_text(device_id, text, return_screenshot=False)`**: Type text directly into the focused field (supports full Unicode on macOS and safe escaping on Android).
- **`press_key(device_id, key, modifiers=[], return_screenshot=False)`**: Press special keys and hotkeys (e.g., `cmd+c`, `tab`, `enter`, `escape`, or Android's `home`, `back`, `recents`, `wakeup`).
- **`drag(device_id, from_x, from_y, to_x, to_y, return_screenshot=False)`**: Drag items on macOS or execute swipe gestures on Android.
- **`scroll(device_id, x=0, y=0, delta_x=0, delta_y=-50, return_screenshot=False)`**: Scroll pages or lists smoothly with pixel-level precision.

### 4. Application & System Control
- **`open_app(device_id, app_name)`**: Launch or focus an application by name (e.g. `"Safari"`, `"Notes"`, `"Chrome"`) or Android package.
- **`open_url(device_id, url)`**: Open a web URL directly in the device's default browser.

### 5. Safety, Guardrails & Kill-Switch
- **`emergency_stop()`**: **Global Emergency Kill-Switch** — immediately halts all device actions and locks out tool execution until explicitly resumed.
- **`resume_control()`**: Resumes normal operation after an emergency stop.
- **`get_safety_status()`**: Inspect current guardrail configuration, emergency stop status, blocked actions count, and rate limiter metrics.

---

## 🛡️ Safety & Guardrails System

The server runs with **Strict Safety Guardrails** enabled by default:
1. **Destructive Command Blocking**: Prohibits dangerous terminal commands (`rm -rf`, `format`, `dd`) and destructive shortcuts (`Cmd+Q`, `Cmd+Alt+Esc`).
2. **Protected App Blacklist**: Blocks attempts to open or automate sensitive system apps like *Keychain Access*, *1Password*, *Bitwarden*, and *Security Settings*.
3. **Emergency Kill-Switch**: The `emergency_stop` tool instantly freezes all input injection and screen interactions across all devices.
4. **Tamper-Evident Audit Trail**: Every action, timestamp, target device, and authorization status is logged to `~/.computer-use-tool/audit.log`.

---

## 🧪 Testing & Verification

The codebase includes an exhaustive master integration test suite and individual milestone suites:

```bash
# Run the Master End-to-End Integration Suite (100% automated):
./run.sh --test

# Run individual milestone suites:
python3 tests/test_milestone1.py  # Mac screenshot & click
python3 tests/test_milestone2.py  # Mac keyboard, drag, scroll, UI tree
python3 tests/test_milestone3.py  # Android screen, taps, gestures, UI tree
python3 tests/test_milestone4.py  # Cross-device coordination & normalization
python3 tests/test_milestone5.py  # Safety guardrails, kill-switch & rate limiter
```

---

## 📁 Repository Structure

```
computer-use-tool/
├── run.sh                       # Turnkey launcher script (status, test, mcp)
├── setup.sh                     # Initial environment & dependency installer
├── pyproject.toml               # Python package configuration
├── config/                      # Turnkey client configurations
│   ├── claude_desktop_config.json # Claude Desktop snippet
│   ├── cursor_mcp.json          # Cursor IDE snippet
│   └── default.toml             # Safety & server tuning
├── src/
│   ├── server.py                # MCP Server definition (17 tools)
│   ├── registry.py              # Dynamic hardware device discovery
│   ├── router.py                # Unified tool routing with persistent IPC
│   ├── adapters/
│   │   ├── base.py              # Common abstract adapter interface
│   │   ├── macos_adapter.py     # Swift daemon IPC with auto-healing
│   │   └── android_adapter.py   # ADB-based high-performance Android engine
│   ├── safety/
│   │   └── guardrails.py        # Strict guardrails, kill-switch & audit trail
│   ├── utils/
│   │   ├── ui_tree.py           # Cross-platform normalized UI tree
│   │   ├── image.py             # Downscaling & format optimization
│   │   └── coordinates.py       # Multi-resolution remapping
│   └── tools/                   # Registered MCP tool implementations
│       ├── observe.py
│       ├── interact.py
│       └── safety.py
├── native/                      # High-speed native Swift daemon
│   ├── Package.swift
│   └── Sources/
│       ├── main.swift           # POSIX Unix domain socket server
│       ├── ScreenCapture.swift  # ScreenCaptureKit frame capture
│       ├── InputInjection.swift # CGEvent mouse/keyboard injection
│       ├── Accessibility.swift  # AXUIElement tree inspection
│       ├── AppManager.swift     # Synchronous app launching
│       └── Protocol.swift       # Strongly-typed JSON IPC protocol
└── tests/                       # Comprehensive verification test suites
    ├── test_milestone1.py
    ├── test_milestone2.py
    ├── test_milestone3.py
    ├── test_milestone4.py
    ├── test_milestone5.py
    └── test_master_integration.py # Master E2E integration test suite
```
