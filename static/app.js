// Minimal chat client: POST /api/chat, render both sides, keep a conversation_id
// so the server can resume the SDK session for follow-up messages (Task 7).

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("composer");
const inputEl = document.getElementById("input");
const sendEl = document.getElementById("send");

// Persist one conversation id for this browser tab.
let conversationId = sessionStorage.getItem("conversation_id") || crypto.randomUUID();
sessionStorage.setItem("conversation_id", conversationId);

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
    // Stream the agent's work via Server-Sent Events (Activity #1). We use
    // fetch (not EventSource) so we can POST the message body.
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, conversation_id: conversationId }),
    });
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line.
      const frames = buffer.split("\n\n");
      buffer = frames.pop(); // keep the trailing partial frame
      for (const frame of frames) {
        const evt = parseSSE(frame);
        if (!evt) continue;
        if (evt.event === "tool") {
          // Live status: show what the agent is doing right now.
          pending.textContent = "🔧 " + evt.data.text;
        } else if (evt.event === "done") {
          if (evt.data.conversation_id) {
            conversationId = evt.data.conversation_id;
            sessionStorage.setItem("conversation_id", conversationId);
          }
          pending.classList.remove("msg--pending");
          pending.textContent = evt.data.reply;
        }
      }
    }
  } catch (err) {
    pending.classList.remove("msg--pending");
    pending.textContent = `⚠️ Could not reach the server (${err.message}).`;
  }
}

// Parse one SSE frame ("event: <type>\ndata: <json>") into {event, data}.
function parseSSE(frame) {
  let event = "message";
  let dataStr = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
  }
  if (!dataStr) return null;
  try {
    return { event, data: JSON.parse(dataStr) };
  } catch {
    return null;
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

// Greeting.
addMessage("assistant", "Hi! I'm the concierge for this repository. Ask me anything about it.");
