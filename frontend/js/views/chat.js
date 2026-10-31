// Lex chatbot widget (rubric 3.3). Owner: Member B. Backend (/chat, Lex bot) is Member C.
import { post } from "../api.js";
import { h } from "../dom.js";

const URL_RE = /(https?:\/\/[^\s]+)/g;

/** Append a chat bubble, turning URLs into clickable links. */
function addMessage(log, text, mine) {
  const row = h("div", {
    class: "chat-message-row" + (mine ? " user" : " bot")
  });

  const bubble = h("div", {
    class: "chat-bubble" + (mine ? " user" : " bot")
  });

  const label = h("div", {
    class: "chat-bubble-label"
  }, mine ? "You" : "EcoGuard");

  const body = h("div", { class: "chat-bubble-body" });

  text.split(URL_RE).forEach((part, i) => {
    if (i % 2) {
      body.append(
        h("a", {
          href: part,
          target: "_blank",
          rel: "noopener noreferrer"
        }, "open")
      );
    } else {
      body.append(document.createTextNode(part));
    }
  });

  bubble.append(label, body);
  row.append(bubble);
  log.append(row);
  log.scrollTop = log.scrollHeight;
}


export function mount(root) {
  const log = h("div", { class: "chat-log", "aria-live": "polite" });
  const input = h("input", { type: "text", id: "chat-text", placeholder: "Show me all photos of foxes" });
  let sessionId;

  const send = async () => {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMessage(log, text, true);
    try {
      const out = await post("/chat", { text, session_id: sessionId });
      sessionId = out.session_id;
      (out.messages.length ? out.messages : ["(no reply)"]).forEach((m) => addMessage(log, m, false));
    } catch (err) {
      addMessage(log, "Error: " + err.message, false);
    }
  };
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });

  root.append(
    h("h2", {}, "Ask EcoGuard"),
    h("p", { class: "hint" }, 'Try "Show me all photos of foxes spotted yesterday" or "Help me find a lost ginger cat".'),
    log,
    h("label", { for: "chat-text" }, "Message"),
    input,
    h("div", { class: "row" }, h("button", { type: "button", onclick: send }, "Send")),
  );
}
