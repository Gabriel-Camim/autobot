import { useMemo, useState } from "react";

import ChatBox from "./components/ChatBox.jsx";
import ContactBar from "./components/ContactBar.jsx";
import ExtractGabrielButton from "./components/ExtractGabrielButton.jsx";
import GalleryModal from "./components/GalleryModal.jsx";
import MindMap, { MIND_MAP_NODES } from "./components/MindMap.jsx";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getSessionId() {
  const key = "gabriel-agent-session-id";
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;
  const created = crypto.randomUUID();
  window.localStorage.setItem(key, created);
  return created;
}

function friendlyError(error) {
  if (!error) return "Algo saiu do fluxo no backend. Tente novamente.";
  if (error.message) return error.message;
  return "Algo saiu do fluxo no backend. Tente novamente.";
}

async function parseApiError(response) {
  try {
    const data = await response.json();
    return new Error(data.message || data.detail || `Erro ${response.status}`);
  } catch {
    return new Error(`Erro ${response.status}`);
  }
}

export default function App() {
  const [sessionId, setSessionId] = useState(() => getSessionId());
  const [activeNode, setActiveNode] = useState("gabriel");
  const [loading, setLoading] = useState(null);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: "intro",
      role: "assistant",
      content:
        "Oi, eu sou o Gabriel. Posso falar sobre minha trajetória, projetos, stack, forma de pensar e como conecto dados, IA, automações e sistemas.",
    },
  ]);

  const activeNodeData = useMemo(
    () => MIND_MAP_NODES.find((node) => node.id === activeNode),
    [activeNode],
  );

  function pushMessage(message) {
    setMessages((current) => [...current, { id: crypto.randomUUID(), ...message }]);
  }

  async function sendText(text) {
    const cleanText = text.trim();
    if (!cleanText || loading) return;

    pushMessage({ role: "user", content: cleanText });
    setLoading("thinking");

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: cleanText,
          session_id: sessionId,
          active_node: activeNode,
        }),
      });
      if (!response.ok) throw await parseApiError(response);

      const data = await response.json();
      setSessionId(data.session_id);
      window.localStorage.setItem("gabriel-agent-session-id", data.session_id);
      pushMessage({
        role: "assistant",
        content: data.answer,
        usage: data.usage,
      });
    } catch (error) {
      pushMessage({ role: "system", content: friendlyError(error) });
    } finally {
      setLoading(null);
    }
  }

  async function sendAudio(blob) {
    if (!blob || loading) return;

    setLoading("transcribing");
    const formData = new FormData();
    formData.append("file", blob, "gabriel-question.webm");
    formData.append("session_id", sessionId);
    formData.append("active_node", activeNode);

    try {
      const response = await fetch(`${API_URL}/voice/chat`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw await parseApiError(response);

      const data = await response.json();
      setSessionId(data.session_id);
      window.localStorage.setItem("gabriel-agent-session-id", data.session_id);
      pushMessage({ role: "user", content: data.transcript || "Audio enviado." });
      pushMessage({
        role: "assistant",
        content: data.answer,
        audioBase64: data.audio_base64,
        audioMimeType: data.audio_mime_type,
        ttsError: data.tts_error,
        usage: data.usage,
      });
      if (data.tts_error) {
        pushMessage({ role: "system", content: data.tts_error });
      }
    } catch (error) {
      pushMessage({ role: "system", content: friendlyError(error) });
    } finally {
      setLoading(null);
    }
  }

  function handleDownloadError(message) {
    pushMessage({ role: "system", content: message });
  }

  async function loadNodeReport(nodeId) {
    if (loading) return;
    setActiveNode(nodeId);
    setLoading("report");

    try {
      const response = await fetch(`${API_URL}/reports/${nodeId}`);
      if (!response.ok) throw await parseApiError(response);
      const data = await response.json();
      pushMessage({
        role: "assistant",
        kind: "report",
        content: data.content,
        title: data.title,
      });
    } catch (error) {
      pushMessage({ role: "system", content: friendlyError(error) });
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="app-shell">
      <section className="map-zone" aria-label="Mapa mental do Gabriel">
        <div className="top-bar">
          <div>
            <ContactBar />
            <h1>Dados, IA, automações e sistemas</h1>
          </div>
          <div className="top-actions">
            <a className="whatsapp-button" href="https://wa.link/rixmac" target="_blank" rel="noreferrer">
              WhatsApp
            </a>
            <ExtractGabrielButton apiUrl={API_URL} onError={handleDownloadError} />
          </div>
        </div>
        <MindMap activeNode={activeNode} onSelect={setActiveNode} onPlayReport={loadNodeReport} />
      </section>

      <section className="chat-zone" aria-label="Conversa com Gabriel">
        <div className="context-strip">
          <span className="context-kicker">Tema</span>
          <strong>{activeNodeData?.label}</strong>
          <span>{activeNodeData?.summary}</span>
        </div>
        <ChatBox
          messages={messages}
          loading={loading}
          onSend={sendText}
          onAudio={sendAudio}
          onVoiceError={(message) => pushMessage({ role: "system", content: message })}
        />
      </section>
      <button
        type="button"
        className="gallery-fab"
        title="Abrir galeria"
        onClick={() => setGalleryOpen(true)}
      >
        <img src="/gallery/polaroids-button.png" alt="" />
      </button>
      <GalleryModal open={galleryOpen} onClose={() => setGalleryOpen(false)} />
    </main>
  );
}
