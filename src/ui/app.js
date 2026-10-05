// app.js — Dynamic Chatbot System with Full Recents History & Persistence

let chatSessions = [];
let currentChatId = null;
let isBusy = false;
let currentDevice = "mac-primary";

const promptInput = document.getElementById("prompt-input");
const btnSend = document.getElementById("btn-send");
const heroState = document.getElementById("hero-state");
const messagesList = document.getElementById("messages-list");
const chatStream = document.getElementById("chat-stream");
const recentsList = document.getElementById("recents-list");
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

// ── Chat Session Management ──────────────────────────────────────

function initChats() {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.get_all_chats().then((chats) => {
      chatSessions = Array.isArray(chats) ? chats : [];
      renderRecents();
      if (chatSessions.length > 0) {
        switchChat(chatSessions[0].id);
      } else {
        createNewChat();
      }
    }).catch((err) => {
      console.warn("Could not load chats from API:", err);
      createNewChat();
    });
  } else {
    // LocalStorage fallback for web browser testing
    try {
      const stored = localStorage.getItem("codex_chats");
      if (stored) chatSessions = JSON.parse(stored);
    } catch (e) {}
    renderRecents();
    if (chatSessions.length > 0) {
      switchChat(chatSessions[0].id);
    } else {
      createNewChat();
    }
  }
}

function renderRecents() {
  recentsList.innerHTML = "";

  if (chatSessions.length === 0) {
    recentsList.innerHTML = `<div class="sidebar-item empty">No recent chats</div>`;
    return;
  }

  chatSessions.forEach((chat) => {
    const item = document.createElement("div");
    item.className = "sidebar-item" + (chat.id === currentChatId ? " active" : "");
    item.onclick = () => switchChat(chat.id);

    const titleSpan = document.createElement("span");
    titleSpan.className = "sidebar-chat-title";
    titleSpan.textContent = chat.title || "Untitled Chat";

    // Trash / Delete Button
    const delBtn = document.createElement("span");
    delBtn.className = "sidebar-chat-del";
    delBtn.title = "Delete chat";
    delBtn.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
      </svg>
    `;
    delBtn.onclick = (e) => {
      e.stopPropagation();
      deleteChat(chat.id);
    };

    item.appendChild(titleSpan);
    item.appendChild(delBtn);
    recentsList.appendChild(item);
  });
}

function createNewChat() {
  currentChatId = "chat_" + Date.now();
  messagesList.innerHTML = "";
  if (heroState) heroState.style.display = "flex";
  promptInput.value = "";
  promptInput.style.height = "auto";
  promptInput.focus();

  // Highlight in sidebar
  renderRecents();
}

function switchChat(chatId) {
  const chat = chatSessions.find((c) => c.id === chatId);
  if (!chat) return;

  currentChatId = chatId;
  messagesList.innerHTML = "";

  if (!chat.messages || chat.messages.length === 0) {
    if (heroState) heroState.style.display = "flex";
  } else {
    if (heroState) heroState.style.display = "none";
    chat.messages.forEach((msg) => {
      if (msg.role === "user") {
        appendUserMessageToDOM(msg.content);
      } else if (msg.role === "assistant") {
        if (msg.actions && Array.isArray(msg.actions)) {
          msg.actions.forEach((act) => appendActionPillToDOM(act.tool, act.desc));
        }
        appendAssistantMessageToDOM(msg.content);
      }
    });
  }

  renderRecents();
  scrollToBottom();
  promptInput.focus();
}

function deleteChat(chatId) {
  chatSessions = chatSessions.filter((c) => c.id !== chatId);

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.delete_chat_session(chatId);
  } else {
    try {
      localStorage.setItem("codex_chats", JSON.stringify(chatSessions));
    } catch (e) {}
  }

  if (currentChatId === chatId) {
    if (chatSessions.length > 0) {
      switchChat(chatSessions[0].id);
    } else {
      createNewChat();
    }
  } else {
    renderRecents();
  }
}

function saveCurrentChat(chat) {
  const idx = chatSessions.findIndex((c) => c.id === chat.id);
  if (idx >= 0) {
    chatSessions[idx] = chat;
  } else {
    chatSessions.unshift(chat);
  }

  renderRecents();

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.save_chat_session(chat);
  } else {
    try {
      localStorage.setItem("codex_chats", JSON.stringify(chatSessions));
    } catch (e) {}
  }
}

// ── Sending & Execution ──────────────────────────────────────────

function sendMessage() {
  const text = promptInput.value.trim();
  if (!text || isBusy) return;

  promptInput.value = "";
  promptInput.style.height = "auto";

  // Hide hero if visible
  if (heroState) heroState.style.display = "none";

  // Ensure active chat session
  let chat = chatSessions.find((c) => c.id === currentChatId);
  if (!chat) {
    chat = {
      id: currentChatId || ("chat_" + Date.now()),
      title: formatChatTitle(text),
      created_at: Date.now(),
      messages: []
    };
    currentChatId = chat.id;
    chatSessions.unshift(chat);
  } else if (!chat.title || chat.title === "New chat" || chat.messages.length === 0) {
    chat.title = formatChatTitle(text);
  }

  // Record user message
  const userMsg = { role: "user", content: text, timestamp: Date.now() };
  chat.messages.push(userMsg);
  appendUserMessageToDOM(text);

  saveCurrentChat(chat);
  setBusyState(true);

  let currentActions = [];

  // Hook for live action callback
  window.onPyAction = function(toolName, desc) {
    currentActions.push({ tool: toolName, desc: desc });
    appendActionPillToDOM(toolName, desc);
  };

  // Call Backend Python API
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.send_message(text, currentDevice, currentChatId)
      .then((res) => {
        const replyText = typeof res === "object" ? res.reply : res;
        const actions = (typeof res === "object" && res.actions) ? res.actions : currentActions;

        const aiMsg = {
          role: "assistant",
          content: replyText,
          actions: actions,
          timestamp: Date.now()
        };
        chat.messages.push(aiMsg);
        saveCurrentChat(chat);

        appendAssistantMessageToDOM(replyText);
        setBusyState(false);
      })
      .catch((err) => {
        const errText = "❌ Error: " + err;
        appendAssistantMessageToDOM(errText);
        setBusyState(false);
      });
  } else {
    // Local simulation fallback
    setTimeout(() => {
      appendActionPillToDOM("open_app", "Executing on " + currentDevice);
      setTimeout(() => {
        const simReply = "Simulated response for: \"" + text + "\"";
        appendAssistantMessageToDOM(simReply);
        chat.messages.push({
          role: "assistant",
          content: simReply,
          actions: [{ tool: "open_app", desc: "Executing on " + currentDevice }],
          timestamp: Date.now()
        });
        saveCurrentChat(chat);
        setBusyState(false);
      }, 700);
    }, 400);
  }
}

function formatChatTitle(raw) {
  let clean = raw.trim().replace(/^open\s+/i, "Open ");
  if (clean.length > 32) {
    clean = clean.substring(0, 30) + "...";
  }
  return clean.charAt(0).toUpperCase() + clean.slice(1);
}

// ── DOM Append Helpers ───────────────────────────────────────────

function appendUserMessageToDOM(text) {
  const row = document.createElement("div");
  row.className = "message-row user";
  row.innerHTML = `<div class="user-bubble">${escapeHtml(text)}</div>`;
  messagesList.appendChild(row);
  scrollToBottom();
}

function appendAssistantMessageToDOM(text) {
  const row = document.createElement("div");
  row.className = "message-row assistant";

  let formatted = escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code style='background:#2d2d34;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:12px;'>$1</code>")
    .replace(/\n/g, "<br/>");

  row.innerHTML = `<div class="assistant-bubble">${formatted}</div>`;
  messagesList.appendChild(row);
  scrollToBottom();
}

function appendActionPillToDOM(toolName, desc) {
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

// ── Sidebar & Topbar Handlers ────────────────────────────────────

document.getElementById("btn-new-chat").addEventListener("click", createNewChat);
document.getElementById("btn-new-tab").addEventListener("click", createNewChat);
document.getElementById("btn-nav-home").addEventListener("click", createNewChat);

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
      appendAssistantMessageToDOM("✅ Settings saved! Target device: **" + currentDevice + "**.");
    });
  } else {
    closeSettingsModal();
  }
});

// Initialize on PyWebview load
window.addEventListener("pywebviewready", () => {
  initChats();
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

// Fallback init for standard browser test
window.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    if (!window.pywebview) {
      initChats();
    }
  }, 100);
});
