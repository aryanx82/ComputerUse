// app.js — Frontend client logic for Computer Use Codex UI

let isBusy = false;
let currentDevice = "mac-primary";

const promptInput = document.getElementById("prompt-input");
const btnSend = document.getElementById("btn-send");
const heroState = document.getElementById("hero-state");
const messagesList = document.getElementById("messages-list");
const chatStream = document.getElementById("chat-stream");
const deviceLabel = document.getElementById("device-label");
const settingsModal = document.getElementById("settings-modal");
const groqKeyInput = document.getElementById("groq-key-input");
const deviceSelectDropdown = document.getElementById("device-select-dropdown");

// Auto-expand textarea as user types
promptInput.addEventListener("input", () => {
  promptInput.style.height = "auto";
  promptInput.style.height = Math.min(promptInput.scrollHeight, 120) + "px";
});

// Enter key to send (Shift+Enter for newline)
promptInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

btnSend.addEventListener("click", sendMessage);

// Send message
function sendMessage() {
  const text = promptInput.value.trim();
  if (!text || isBusy) return;

  promptInput.value = "";
  promptInput.style.height = "auto";

  // Hide hero if visible
  if (heroState) {
    heroState.style.display = "none";
  }

  // Render User Message
  appendUserMessage(text);

  // Set busy state
  setBusyState(true);

  // Call Python Backend API
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.send_message(text, currentDevice)
      .then((reply) => {
        appendAssistantMessage(reply);
        setBusyState(false);
      })
      .catch((err) => {
        appendAssistantMessage("❌ Error: " + err);
        setBusyState(false);
      });
  } else {
    // Fallback simulation if testing in standard browser
    setTimeout(() => {
      appendActionPill("open_app", "Executing action on " + currentDevice);
      setTimeout(() => {
        appendAssistantMessage("I received: \"" + text + "\". (PyWebview bridge connected)");
        setBusyState(false);
      }, 700);
    }, 400);
  }
}

function appendUserMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row user";
  row.innerHTML = `<div class="user-bubble">${escapeHtml(text)}</div>`;
  messagesList.appendChild(row);
  scrollToBottom();
}

function appendAssistantMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row assistant";

  // Convert basic markdown like **bold**, *italic*, `code`
  let formatted = escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code style='background:#2d2d34;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:12px;'>$1</code>")
    .replace(/\n/g, "<br/>");

  row.innerHTML = `<div class="assistant-bubble">${formatted}</div>`;
  messagesList.appendChild(row);
  scrollToBottom();
}

function appendActionPill(toolName, desc) {
  let icon = "⚡";
  if (toolName.includes("open")) icon = "🚀";
  else if (toolName.includes("type")) icon = "⌨️";
  else if (toolName.includes("press")) icon = "🔤";
  else if (toolName.includes("click")) icon = "🖱️";
  else if (toolName.includes("screenshot")) icon = "📸";

  const pill = document.createElement("div");
  pill.className = "action-card";
  pill.innerHTML = `<span>${icon}</span> <span>${escapeHtml(desc)}</span>`;
  messagesList.appendChild(pill);
  scrollToBottom();
}

function appendScreenshotPreview(base64Data) {
  const preview = document.createElement("div");
  preview.className = "screenshot-preview";
  preview.innerHTML = `<img src="data:image/jpeg;base64,${base64Data}" alt="Captured Screen" />`;
  messagesList.appendChild(preview);
  scrollToBottom();
}

function scrollToBottom() {
  chatStream.scrollTop = chatStream.scrollHeight;
}

function setBusyState(busy) {
  isBusy = busy;
  btnSend.disabled = busy;
  if (busy) {
    promptInput.placeholder = "Executing on your device...";
  } else {
    promptInput.placeholder = "Do anything";
    promptInput.focus();
  }
}

function escapeHtml(string) {
  const entityMap = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  };
  return String(string).replace(/[&<>"']/g, (s) => entityMap[s]);
}

// ── Sidebar Interactions ─────────────────────────────────────────

function useRecent(text) {
  promptInput.value = text;
  promptInput.focus();
  sendMessage();
}

document.getElementById("btn-new-chat").addEventListener("click", () => {
  messagesList.innerHTML = "";
  if (heroState) heroState.style.display = "flex";
  promptInput.value = "";
  promptInput.focus();
});

document.getElementById("btn-new-tab").addEventListener("click", () => {
  document.getElementById("btn-new-chat").click();
});

// ── Modal & Settings ─────────────────────────────────────────────

const btnOpenSettings = document.getElementById("btn-open-settings");
const btnGetPlus = document.getElementById("btn-get-plus");
const btnModelSelector = document.getElementById("btn-model-selector");
const btnChooseDevice = document.getElementById("btn-choose-device");
const btnCancelModal = document.getElementById("btn-cancel-modal");
const btnSaveModal = document.getElementById("btn-save-modal");

function openSettingsModal() {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.get_settings().then((data) => {
      groqKeyInput.value = data.api_key || "";
      deviceSelectDropdown.value = data.target_device || "mac-primary";
    });
  }
  settingsModal.classList.add("open");
  groqKeyInput.focus();
}

function closeSettingsModal() {
  settingsModal.classList.remove("open");
}

btnOpenSettings.addEventListener("click", openSettingsModal);
btnGetPlus.addEventListener("click", openSettingsModal);
btnModelSelector.addEventListener("click", openSettingsModal);
btnChooseDevice.addEventListener("click", openSettingsModal);
btnCancelModal.addEventListener("click", closeSettingsModal);

btnSaveModal.addEventListener("click", () => {
  const key = groqKeyInput.value.trim();
  const device = deviceSelectDropdown.value;

  currentDevice = device;
  deviceLabel.textContent = device === "mac-primary" ? "Mac Primary" : "Android Tablet";

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.save_settings(key, device).then(() => {
      closeSettingsModal();
      appendAssistantMessage("✅ Settings saved! Target device: **" + currentDevice + "**.");
    });
  } else {
    closeSettingsModal();
  }
});

// Initialize on PyWebview load
window.addEventListener("pywebviewready", () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.get_settings().then((data) => {
      currentDevice = data.target_device || "mac-primary";
      deviceLabel.textContent = currentDevice === "mac-primary" ? "Mac Primary" : "Android Tablet";
      if (data.has_key) {
        document.getElementById("model-name-label").textContent = "Llama 3.3 70B ⌵";
      }
    });
  }
});

// Hook for Python to notify frontend of live tool executions
window.onPyAction = function(toolName, desc) {
  appendActionPill(toolName, desc);
};

window.onPyScreenshot = function(b64) {
  appendScreenshotPreview(b64);
};
