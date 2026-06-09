import { Mic, Square } from "lucide-react";
import { useRef, useState } from "react";

export default function VoiceInput({ disabled, onAudio, onError }) {
  const [recording, setRecording] = useState(false);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);

  async function startRecording() {
    if (disabled) return;
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      onError("Gravação de áudio não está disponível neste navegador.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        if (blob.size > 0) onAudio(blob);
      };

      recorder.start();
      setRecording(true);
    } catch {
      onError("Não consegui acessar o microfone.");
    }
  }

  function stopRecording() {
    if (!recorderRef.current || recorderRef.current.state === "inactive") return;
    recorderRef.current.stop();
    recorderRef.current = null;
    setRecording(false);
  }

  return (
    <button
      type="button"
      className={`icon-button voice-button ${recording ? "is-recording" : ""}`}
      title={recording ? "Parar gravação" : "Gravar áudio"}
      onClick={recording ? stopRecording : startRecording}
      disabled={disabled && !recording}
    >
      {recording ? <Square size={18} aria-hidden="true" /> : <Mic size={20} aria-hidden="true" />}
    </button>
  );
}
