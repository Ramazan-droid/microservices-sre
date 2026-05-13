import { useState } from "react";

export default function Chat() {
  const [from, setFrom] = useState(1);
  const [to, setTo] = useState(2);
  const [msg, setMsg] = useState("");
  const [messages, setMessages] = useState([]);

  async function sendMessage() {
    try {
      const r = await fetch("/chat-svc/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sender_id: parseInt(from),
          receiver_id: parseInt(to),
          content: msg,
        }),
      });

      if (r.ok) {
        setMsg("");
        loadMessages();
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function loadMessages() {
    try {
      const r = await fetch(`/chat-svc/messages/${from}?other_user_id=${to}`);
      const data = await r.json();
      setMessages(data.messages || []);
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div>
      <h2>Chat</h2>

      <div>
        <input value={from} onChange={(e) => setFrom(e.target.value)} placeholder="From user" />
        <input value={to} onChange={(e) => setTo(e.target.value)} placeholder="To user" />
      </div>

      <input value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Message" />

      <button onClick={sendMessage}>Send</button>
      <button onClick={loadMessages}>Load</button>

      <div>
        {messages.map((m, i) => (
          <div key={i} style={{ textAlign: m.sender_id == from ? "right" : "left" }}>
            <div
              style={{
                display: "inline-block",
                padding: "8px",
                margin: "5px",
                background: m.sender_id == from ? "#38bdf8" : "#334155",
                color: "white",
                borderRadius: "8px",
              }}
            >
              {m.content}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}