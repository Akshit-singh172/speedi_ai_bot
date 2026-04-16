/* global window, document, fetch */

const cfg = window.__SPEEDI__ || { apiChatUrl: "/chat", apiHealthUrl: "/api/health" };

const els = {
  messages: document.getElementById("messages"),
  composer: document.getElementById("composer"),
  messageInput: document.getElementById("messageInput"),
  sendBtn: document.getElementById("sendBtn"),
  userIdInput: document.getElementById("userIdInput"),
  resetBtn: document.getElementById("resetBtn"),
  statusDot: document.getElementById("statusDot"),
  statusText: document.getElementById("statusText"),
};

function safeJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function genId() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `user_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function getUserId() {
  const stored = localStorage.getItem("speedi_user_id");
  if (stored) return stored;
  const created = genId();
  localStorage.setItem("speedi_user_id", created);
  return created;
}

function setUserId(next) {
  const trimmed = String(next || "").trim();
  if (!trimmed) return;
  localStorage.setItem("speedi_user_id", trimmed);
}

function setStatus(ok, text) {
  els.statusDot.classList.toggle("ok", !!ok);
  els.statusDot.classList.toggle("bad", !ok);
  els.statusText.textContent = text;
}

async function checkHealth() {
  try {
    const res = await fetch(cfg.apiHealthUrl, { method: "GET" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    setStatus(true, "Online");
  } catch (e) {
    setStatus(false, "Offline");
  }
}

function scrollToBottom() {
  els.messages.scrollTop = els.messages.scrollHeight;
}

function addBubble(role, nodes) {
  const row = document.createElement("div");
  row.className = `row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (Array.isArray(nodes)) {
    nodes.forEach((n) => bubble.appendChild(n));
  } else if (nodes) {
    bubble.appendChild(nodes);
  }

  row.appendChild(bubble);
  els.messages.appendChild(row);
  scrollToBottom();

  return { row, bubble };
}

function textNode(text) {
  const p = document.createElement("div");
  p.className = "text";
  p.textContent = text;
  return p;
}

function codeNode(obj) {
  const pre = document.createElement("pre");
  pre.className = "code";
  pre.textContent = typeof obj === "string" ? obj : safeJson(obj);
  return pre;
}

function imageNode(url) {
  const wrap = document.createElement("div");
  wrap.className = "image-wrap";

  const img = document.createElement("img");
  img.className = "image";
  img.alt = "Generated image";
  img.loading = "lazy";
  img.src = url;

  const a = document.createElement("a");
  a.className = "image-link";
  a.href = url;
  a.target = "_blank";
  a.rel = "noreferrer";
  a.textContent = "Open image";

  wrap.appendChild(img);
  wrap.appendChild(a);
  return wrap;
}

function renderReply(reply) {
  if (reply == null) return [textNode("No response")];

  if (typeof reply === "string") return [textNode(reply)];

  if (typeof reply !== "object") return [textNode(String(reply))];

  const nodes = [];
  if (typeof reply.message === "string" && reply.message.trim()) {
    nodes.push(textNode(reply.message));
  }

  if (reply.type === "image") {
    const data = reply.data;
    if (Array.isArray(data)) {
      data.forEach((item) => {
        if (item && typeof item === "object" && typeof item.url === "string" && item.url.trim()) {
          nodes.push(imageNode(item.url));
        }
      });
    }
    if (nodes.length === 0) nodes.push(textNode("Image generated."));
    return nodes;
  }

  if (reply.type === "message") {
    if (typeof reply.data === "string" && reply.data.trim()) {
      nodes.push(textNode(reply.data));
      return nodes;
    }
  }

  if (reply.data !== undefined) {
    nodes.push(codeNode(reply.data));
  } else {
    nodes.push(codeNode(reply));
  }

  return nodes;
}

let pending = false;

async function sendMessage(message) {
  if (pending) return;
  pending = true;
  els.sendBtn.disabled = true;

  const userId = els.userIdInput.value.trim() || getUserId();
  setUserId(userId);
  els.userIdInput.value = userId;

  const thinking = addBubble("assistant", textNode("Thinking…"));

  try {
    const res = await fetch(cfg.apiChatUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, user_id: userId }),
    });

    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(payload.error || `Request failed (HTTP ${res.status})`);
    }

    thinking.row.remove();

    const reply = payload.reply ?? payload;
    addBubble("assistant", renderReply(reply));
  } catch (e) {
    thinking.row.remove();
    addBubble("assistant", [textNode("Error"), codeNode(String(e && e.message ? e.message : e))]);
    await checkHealth();
  } finally {
    pending = false;
    els.sendBtn.disabled = false;
    els.messageInput.focus();
  }
}

function autoGrow(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
}

function resetChat() {
  els.messages.innerHTML = "";
  addBubble("assistant", textNode("Hi! How can I help? You can also ask me to generate an image."));
}

els.composer.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = els.messageInput.value.trim();
  if (!message) return;

  els.messageInput.value = "";
  autoGrow(els.messageInput);

  addBubble("user", textNode(message));
  await sendMessage(message);
});

els.messageInput.addEventListener("input", () => autoGrow(els.messageInput));
els.messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    els.composer.requestSubmit();
  }
});

els.userIdInput.addEventListener("change", () => setUserId(els.userIdInput.value));
// Reset button handler is defined at the end (needs current user id).

// Init
els.userIdInput.value = getUserId();
resetChat();
checkHealth();

els.resetBtn.addEventListener("click", async () => {
  resetChat();
  const userId = els.userIdInput.value.trim() || getUserId();
  setUserId(userId);
  els.userIdInput.value = userId;
  try {
    await fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });
  } catch {
    // ignore
  }
});
