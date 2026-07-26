/*
 * Embeddable Website Chatbot Widget (Modern Design)
 * ----------------------------------------------------
 * Client apni website ke <body> mein bas yeh line lagayega:
 *
 *   <script src="https://YOUR-SERVER-DOMAIN/widget.js" data-client-id="CLIENT_ID" data-color="#7c3aed"></script>
 *
 * Yeh script khud bottom-right corner mein ek chat bubble bana deta hai.
 */

(function () {
  const scriptTag = document.currentScript;
  const clientId = scriptTag.getAttribute("data-client-id");
  // const apiBase = new URL(scriptTag.src).origin;
  const apiBase = "https://chatbot-production-eade.up.railway.app";
  const accentColor = scriptTag.getAttribute("data-color") || "#7c3aed";
  const businessName = scriptTag.getAttribute("data-name") || "Assistant";

  if (!clientId) {
    console.error("Chatbot widget: data-client-id missing on script tag.");
    return;
  }

  let history = [];
  let isOpen = false;

  const style = document.createElement("style");
  style.textContent = `
    #cbw-bubble {
      position: fixed; bottom: 24px; right: 24px; width: 62px; height: 62px;
      border-radius: 50%; background: ${accentColor};
      box-shadow: 0 6px 20px rgba(0,0,0,0.25);
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      z-index: 999999; transition: transform 0.2s ease;
    }
    #cbw-bubble:hover { transform: scale(1.07); }
    #cbw-bubble svg { width: 26px; height: 26px; fill: white; }

    #cbw-window {
      position: fixed; bottom: 100px; right: 24px; width: 370px; max-width: 92vw;
      height: 540px; max-height: 78vh; background: #fff; border-radius: 20px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.25); display: none; flex-direction: column;
      overflow: hidden; z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #cbw-window.cbw-open { display: flex; }

    #cbw-header {
      background: linear-gradient(135deg, ${accentColor}, ${accentColor}cc);
      color: #fff; padding: 22px 20px 28px; position: relative;
    }
    #cbw-close {
      position: absolute; top: 14px; right: 16px; cursor: pointer;
      width: 28px; height: 28px; border-radius: 50%; background: rgba(255,255,255,0.18);
      display: flex; align-items: center; justify-content: center;
      font-size: 18px; line-height: 1; transition: background 0.15s ease;
    }
    #cbw-close:hover { background: rgba(255,255,255,0.3); }

    #cbw-header-top { display: flex; align-items: center; gap: 10px; }
    #cbw-avatar {
      width: 38px; height: 38px; border-radius: 50%; background: rgba(255,255,255,0.25);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    #cbw-avatar svg { width: 20px; height: 20px; fill: #fff; }
    #cbw-header-title { font-size: 16px; font-weight: 700; }
    #cbw-header-sub { font-size: 12.5px; opacity: 0.85; margin-top: 1px; }

    #cbw-body-wrap {
      flex: 1; margin-top: -14px; background: #f4f5f7;
      border-top-left-radius: 18px; border-top-right-radius: 18px;
      display: flex; flex-direction: column; overflow: hidden;
    }

    #cbw-messages { flex: 1; overflow-y: auto; padding: 16px 14px; }
    .cbw-msg { margin-bottom: 12px; display: flex; }
    .cbw-msg.user { justify-content: flex-end; }
    .cbw-bubble-text {
      max-width: 82%; padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.45;
      white-space: pre-wrap; word-wrap: break-word;
    }
    .cbw-msg.user .cbw-bubble-text {
      background: ${accentColor}; color: #fff; border-bottom-right-radius: 4px;
    }
    .cbw-msg.bot .cbw-bubble-text {
      background: #fff; color: #26282b; box-shadow: 0 1px 2px rgba(0,0,0,0.06);
      border-bottom-left-radius: 4px;
    }

    #cbw-typing {
      font-size: 12.5px; color: #9095a0; padding: 0 16px 6px; font-style: italic;
    }

    #cbw-input-row {
      display: flex; align-items: center; gap: 8px;
      border-top: 1px solid #e7e8eb; padding: 10px 12px; background: #fff;
    }
    #cbw-input {
      flex: 1; border: none; outline: none; padding: 11px 14px; font-size: 14px;
      border-radius: 22px; background: #f1f2f4; color: #222;
    }
    #cbw-send {
      background: ${accentColor}; color: #fff; border: none; border-radius: 50%;
      width: 40px; height: 40px; flex-shrink: 0; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: opacity 0.15s ease;
    }
    #cbw-send svg { width: 18px; height: 18px; fill: #fff; }
    #cbw-send:disabled { opacity: 0.5; cursor: default; }

    #cbw-footer {
      text-align: center; font-size: 11px; color: #b3b6bd; padding: 6px 0 10px; background: #fff;
    }
  `;
  document.head.appendChild(style);

  const bubble = document.createElement("div");
  bubble.id = "cbw-bubble";
  bubble.innerHTML = `<svg viewBox="0 0 24 24"><path d="M4 4h16v12H5.17L4 17.17V4z"/></svg>`;

  const chatWindow = document.createElement("div");
  chatWindow.id = "cbw-window";
  chatWindow.innerHTML = `
    <div id="cbw-header">
      <div id="cbw-close">&times;</div>
      <div id="cbw-header-top">
        <div id="cbw-avatar">
          <svg viewBox="0 0 24 24"><path d="M12 2a5 5 0 0 1 5 5v2a5 5 0 0 1-10 0V7a5 5 0 0 1 5-5zm-7 17.5C5 16 8 14 12 14s7 2 7 5.5V21H5v-1.5z"/></svg>
        </div>
        <div>
          <div id="cbw-header-title">Hi there 👋</div>
          <div id="cbw-header-sub">${businessName}</div>
        </div>
      </div>
    </div>
    <div id="cbw-body-wrap">
      <div id="cbw-messages"></div>
      <div id="cbw-typing" style="display:none;">Typing...</div>
      <div id="cbw-input-row">
        <input id="cbw-input" type="text" placeholder="Type your message..." />
        <button id="cbw-send">
          <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg>
        </button>
      </div>
      <div id="cbw-footer">Powered by AI Chatbot</div>
    </div>
  `;

  document.body.appendChild(bubble);
  document.body.appendChild(chatWindow);

  const messagesEl = chatWindow.querySelector("#cbw-messages");
  const inputEl = chatWindow.querySelector("#cbw-input");
  const sendBtn = chatWindow.querySelector("#cbw-send");
  const typingEl = chatWindow.querySelector("#cbw-typing");

  function addMessage(role, text) {
    const row = document.createElement("div");
    row.className = `cbw-msg ${role}`;
    const bubbleText = document.createElement("div");
    bubbleText.className = "cbw-bubble-text";
    bubbleText.textContent = text;
    row.appendChild(bubbleText);
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function toggleWindow() {
    isOpen = !isOpen;
    chatWindow.classList.toggle("cbw-open", isOpen);
    if (isOpen && messagesEl.children.length === 0) {
      addMessage("bot", "Hi! How can I help you today?");
    }
  }

  bubble.addEventListener("click", toggleWindow);
  chatWindow.querySelector("#cbw-close").addEventListener("click", toggleWindow);

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    addMessage("user", text);
    inputEl.value = "";
    sendBtn.disabled = true;
    typingEl.style.display = "block";

    try {
      const resp = await fetch(`${apiBase}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: clientId,
          message: text,
          history: history,
        }),
      });

      if (!resp.ok) throw new Error("Server error");
      const data = await resp.json();

      history.push({ role: "user", content: text });
      history.push({ role: "assistant", content: data.reply });

      addMessage("bot", data.reply);
    } catch (err) {
      addMessage("bot", "Sorry, something went wrong. Please try again.");
    } finally {
      sendBtn.disabled = false;
      typingEl.style.display = "none";
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });
})();
