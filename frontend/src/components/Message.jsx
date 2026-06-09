import { CircleAlert, User } from "lucide-react";

function AudioReply({ base64, mimeType }) {
  if (!base64) return null;
  return (
    <audio className="audio-reply" controls src={`data:${mimeType || "audio/mpeg"};base64,${base64}`}>
      Seu navegador não suporta áudio.
    </audio>
  );
}

export default function Message({ message }) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const Icon = isSystem ? CircleAlert : User;

  return (
    <article className={`message ${message.role} ${message.kind || ""}`}>
      <div className="message-avatar" aria-hidden="true">
        {isUser || isSystem ? <Icon size={18} /> : <img src="/gabriel/foto.png" alt="" />}
      </div>
      <div className="message-body">
        {message.title ? <strong className="message-title">{message.title}</strong> : null}
        <p>{message.content}</p>
        <AudioReply base64={message.audioBase64} mimeType={message.audioMimeType} />
      </div>
    </article>
  );
}
