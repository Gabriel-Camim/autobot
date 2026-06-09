import { Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import Message from "./Message.jsx";
import VoiceInput from "./VoiceInput.jsx";

const LOADING_LABELS = {
  thinking: "Pensando",
  transcribing: "Transcrevendo",
  report: "Abrindo relatório",
};

export default function ChatBox({ messages, loading, onSend, onAudio, onVoiceError }) {
  const [draft, setDraft] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading]);

  function submit(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || loading) return;
    setDraft("");
    onSend(text);
  }

  return (
    <div className="chat-box">
      <div className="messages" aria-live="polite">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        {loading ? <div className="loading-pill">{LOADING_LABELS[loading] || "Carregando"}</div> : null}
        <div ref={messagesEndRef} />
      </div>

      <form className="composer" onSubmit={submit}>
        <VoiceInput disabled={Boolean(loading)} onAudio={onAudio} onError={onVoiceError} />
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Pergunte ao Gabriel"
          disabled={Boolean(loading)}
          aria-label="Mensagem"
        />
        <button type="submit" className="icon-button send-button" title="Enviar" disabled={!draft.trim() || Boolean(loading)}>
          <Send size={20} aria-hidden="true" />
        </button>
      </form>
    </div>
  );
}
