// Minimal chat client: POST /api/chat, render both sides, keep a conversation_id
// so the server can resume the SDK session for follow-up messages (Task 7).

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("composer");
const inputEl = document.getElementById("input");
const sendEl = document.getElementById("send");

const gateEl = document.getElementById("gate");
const gateFormEl = document.getElementById("gate-form");
const gateInputEl = document.getElementById("gate-input");
const gateErrorEl = document.getElementById("gate-error");

// Persist one conversation id for this browser tab.
let conversationId = sessionStorage.getItem("conversation_id") || crypto.randomUUID();
sessionStorage.setItem("conversation_id", conversationId);

// Shared password (if the deployment is gated). Kept only for this tab.
let password = sessionStorage.getItem("concierge_password") || "";

// If the server is gated and we don't have a valid password yet, show the
// unlock screen and wait for it before enabling chat.
async function enforceGate() {
  let gated = false;
  try {
    const res = await fetch("/api/health");
    gated = (await res.json()).gated;
  } catch {
    return; // if health fails, let the chat surface the error normally
  }
  if (!gated || password) return;

  gateEl.hidden = false;
  await new Promise((resolve) => {
    gateFormEl.addEventListener("submit", (e) => {
      e.preventDefault();
      password = gateInputEl.value;
      sessionStorage.setItem("concierge_password", password);
      gateEl.hidden = true;
      resolve();
    });
  });
}

function addMessage(role, text, opts = {}) {
  const el = document.createElement("div");
  el.className = `msg msg--${role}` + (opts.pending ? " msg--pending" : "");
  el.textContent = text;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

async function sendMessage(text) {
  addMessage("user", text);
  const pending = addMessage("assistant", "thinking…", { pending: true });

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Concierge-Password": password,
      },
      body: JSON.stringify({ message: text, conversation_id: conversationId }),
    });
    if (res.status === 401) {
      // Password wrong or expired — clear it and show the unlock screen again.
      password = "";
      sessionStorage.removeItem("concierge_password");
      pending.classList.remove("msg--pending");
      pending.textContent = "🔒 Wrong password — please unlock and try again.";
      gateErrorEl.hidden = false;
      await enforceGate();
      return;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Adopt the server's conversation id (it mints one on the first message).
    if (data.conversation_id) {
      conversationId = data.conversation_id;
      sessionStorage.setItem("conversation_id", conversationId);
    }

    pending.classList.remove("msg--pending");
    pending.textContent = data.reply;
  } catch (err) {
    pending.classList.remove("msg--pending");
    pending.textContent = `⚠️ Could not reach the server (${err.message}).`;
  }
}

formEl.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = "";
  inputEl.disabled = true;
  sendEl.disabled = true;
  try {
    await sendMessage(text);
  } finally {
    inputEl.disabled = false;
    sendEl.disabled = false;
    inputEl.focus();
  }
});

// Show the unlock screen first if the deployment is gated, then greet.
enforceGate().then(() => {
  addMessage("assistant", "Hi! I'm the concierge for this repository. Ask me anything about it.");
});
