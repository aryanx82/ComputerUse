#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Computer Use Tool — Unified Runner & Controller
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOCKET_DIR="${HOME}/.computer-use-tool"
SOCKET_PATH="${SOCKET_DIR}/daemon.sock"
LOG_PATH="${SOCKET_DIR}/daemon.log"
NATIVE_DIR="${SCRIPT_DIR}/native"
RELEASE_BIN="${NATIVE_DIR}/.build/release/computer-use-daemon"
DEBUG_BIN="${NATIVE_DIR}/.build/debug/computer-use-daemon"

# Prefer release binary, fall back to debug binary
if [ -x "${RELEASE_BIN}" ]; then
    DAEMON_BIN="${RELEASE_BIN}"
elif [ -x "${DEBUG_BIN}" ]; then
    DAEMON_BIN="${DEBUG_BIN}"
else
    DAEMON_BIN=""
fi

# Detect Python interpreter (prefer project venv if present)
if [ -x "${SCRIPT_DIR}/.venv/bin/python3" ]; then
    PYTHON="${SCRIPT_DIR}/.venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
else
    echo "❌ Error: Python 3 not found. Please install Python 3.11+."
    exit 1
fi

export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

# ── Helper Functions ─────────────────────────────────────────────────────────

is_daemon_running() {
    if pgrep -f "computer-use-daemon" &>/dev/null; then
        return 0
    fi
    return 1
}

build_daemon_if_needed() {
    if [ -z "${DAEMON_BIN}" ] || [ ! -x "${DAEMON_BIN}" ]; then
        echo "🔨 Swift daemon binary not found. Compiling release build..."
        (cd "${NATIVE_DIR}" && swift build -c release)
        if [ -x "${RELEASE_BIN}" ]; then
            DAEMON_BIN="${RELEASE_BIN}"
            echo "   ✅ Compiled: ${DAEMON_BIN}"
        else
            echo "❌ Failed to compile Swift daemon. Check Xcode command line tools."
            exit 1
        fi
    fi
}

start_daemon() {
    build_daemon_if_needed
    mkdir -p "${SOCKET_DIR}"

    if is_daemon_running; then
        echo "ℹ️  Swift daemon is already running."
        return 0
    fi

    # Clean up stale socket
    rm -f "${SOCKET_PATH}"

    echo "🚀 Starting Swift native daemon in background..."
    nohup "${DAEMON_BIN}" > "${LOG_PATH}" 2>&1 &
    DAEMON_PID=$!

    # Wait up to 5 seconds for socket creation
    for i in {1..50}; do
        if [ -S "${SOCKET_PATH}" ]; then
            echo "   ✅ Swift daemon started (PID ${DAEMON_PID}, socket: ${SOCKET_PATH})"
            return 0
        fi
        sleep 0.1
    done

    echo "⚠️  Daemon started (PID ${DAEMON_PID}), but socket not ready after 5s. Check ${LOG_PATH}"
}

stop_daemon() {
    echo "🛑 Stopping Swift daemon..."
    pkill -f "computer-use-daemon" || true
    rm -f "${SOCKET_PATH}"
    echo "   ✅ Swift daemon stopped."
}

show_status() {
    echo "══════════════════════════════════════════════════════"
    echo "  🖥️   Computer Use Tool — System Status"
    echo "══════════════════════════════════════════════════════"

    # Daemon Status
    if is_daemon_running; then
        DAEMON_PIDS=$(pgrep -f "computer-use-daemon" | tr '\n' ' ')
        echo "  • Swift Native Daemon: 🟢 RUNNING (PID: ${DAEMON_PIDS})"
        if [ -S "${SOCKET_PATH}" ]; then
            echo "    Socket: ${SOCKET_PATH} (Active)"
        else
            echo "    Socket: ⚠️ Missing ${SOCKET_PATH}"
        fi
    else
        echo "  • Swift Native Daemon: ⚪ STOPPED"
        echo "    Binary: ${DAEMON_BIN:-Not built}"
    fi

    # Python Environment
    echo "  • Python Interpreter:  $(${PYTHON} --version) (${PYTHON})"

    # Device Discovery
    echo ""
    echo "  📱 Connected Devices:"
    "${PYTHON}" -c "
import os, sys
from src.registry import DeviceRegistry
registry = DeviceRegistry()
devices = registry.list_devices()
for d in devices:
    status_icon = '🟢' if d.status.is_connected else '🔴'
    print(f'    {status_icon} [{d.platform.upper()}] {d.name} (ID: {d.id})')
"
    echo "══════════════════════════════════════════════════════"
}

# ── Argument Parsing ─────────────────────────────────────────────────────────

case "${1:-}" in
    --help|-h)
        echo "Usage: ./run.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  (no args)           Start MCP server in stdio mode (for Claude Desktop / Cursor)"
        echo "  --stdio             Explicitly start MCP server in stdio mode"
        echo "  --status            Check health of Swift daemon and discovered devices"
        echo "  --start-daemon      Start the Swift native daemon in background"
        echo "  --stop-daemon       Stop the running Swift daemon"
        echo "  --restart-daemon    Restart the Swift daemon"
        echo "  --interactive, -i   Launch interactive CLI client to test devices"
        echo "  --test              Run the full master integration test suite"
        echo "  --help, -h          Show this help message"
        exit 0
        ;;
    --status)
        show_status
        exit 0
        ;;
    --start-daemon)
        start_daemon
        exit 0
        ;;
    --stop-daemon)
        stop_daemon
        exit 0
        ;;
    --restart-daemon)
        stop_daemon
        sleep 0.5
        start_daemon
        exit 0
        ;;
    --interactive|-i)
        start_daemon
        exec "${PYTHON}" test_client.py
        ;;
    --test)
        start_daemon
        exec "${PYTHON}" tests/test_master_integration.py
        ;;
    --stdio|"")
        # Ensure daemon is compiled and running
        start_daemon
        # Launch MCP server on stdio
        exec "${PYTHON}" -m src.server
        ;;
    *)
        echo "Unknown option: $1"
        echo "Run './run.sh --help' for usage instructions."
        exit 1
        ;;
esac
