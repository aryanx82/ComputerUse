#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Computer Use Tool — Setup Script
# Installs Python dependencies and builds the Swift native daemon.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NATIVE_DIR="${SCRIPT_DIR}/native"

echo "╔══════════════════════════════════════════════════════╗"
echo "║        Computer Use Tool — Setup                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Check prerequisites ──────────────────────────────────────
echo "📋 Checking prerequisites..."

# Check for Python 3.11+
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "   ✅ Python ${PYTHON_VERSION}"

# Check for Swift
if ! command -v swift &>/dev/null; then
    echo "❌ Swift not found. Please install Xcode or Xcode Command Line Tools."
    echo "   Run: xcode-select --install"
    exit 1
fi

SWIFT_VERSION=$(swift --version 2>&1 | head -1)
echo "   ✅ ${SWIFT_VERSION}"

# Check for uv (preferred) or pip
if command -v uv &>/dev/null; then
    INSTALLER="uv"
    echo "   ✅ uv package manager found"
elif command -v pip3 &>/dev/null; then
    INSTALLER="pip"
    echo "   ✅ pip3 found (consider installing 'uv' for faster installs)"
else
    echo "❌ Neither uv nor pip3 found. Please install Python package manager."
    exit 1
fi

echo ""

# ── Step 2: Install Python dependencies ──────────────────────────────
echo "📦 Installing Python dependencies..."

if [ "$INSTALLER" = "uv" ]; then
    # Create venv if it doesn't exist
    if [ ! -d "${SCRIPT_DIR}/.venv" ]; then
        uv venv "${SCRIPT_DIR}/.venv"
    fi
    uv pip install --python "${SCRIPT_DIR}/.venv/bin/python" \
        "mcp[cli]>=1.2.0" "pillow>=10.0.0" "pydantic>=2.0.0"
    echo "   ✅ Dependencies installed in .venv/"
    echo "   💡 Activate with: source .venv/bin/activate"
else
    pip3 install "mcp[cli]>=1.2.0" "pillow>=10.0.0" "pydantic>=2.0.0"
    echo "   ✅ Dependencies installed"
fi

echo ""

# ── Step 3: Build Swift daemon ───────────────────────────────────────
echo "🔨 Building Swift native daemon..."
cd "${NATIVE_DIR}"
swift build 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ Swift daemon built successfully"
    echo "   📍 Binary at: ${NATIVE_DIR}/.build/debug/computer-use-daemon"
else
    echo "   ⚠️  Swift build failed. You may need to build manually:"
    echo "      cd native && swift build"
fi

cd "${SCRIPT_DIR}"
echo ""

# ── Step 4: Create daemon socket directory ───────────────────────────
mkdir -p ~/.computer-use-tool
echo "   ✅ Created ~/.computer-use-tool/"

echo ""

# ── Step 5: macOS permissions reminder ───────────────────────────────
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ⚠️  IMPORTANT: macOS Permissions Required          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "The daemon needs TWO macOS permissions to work:"
echo ""
echo "1. 🖥️  SCREEN RECORDING (for taking screenshots)"
echo "   System Settings → Privacy & Security → Screen Recording"
echo "   → Add the Terminal app (or whichever app runs the daemon)"
echo ""
echo "2. 🖱️  ACCESSIBILITY (for mouse/keyboard control)"
echo "   System Settings → Privacy & Security → Accessibility"
echo "   → Add the Terminal app (or whichever app runs the daemon)"
echo ""
echo "The daemon will prompt you for these on first run."
echo ""

echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅  Setup Complete!                                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Quick Start:"
echo "  1. Start the daemon:    cd native && .build/debug/computer-use-daemon"
echo "  2. In another terminal: python3 test_client.py"
echo ""
