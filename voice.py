from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from openai import OpenAI, OpenAIError

from agent import AppError
from config import Settings, get_settings


SUPPORTED_AUDIO_SUFFIXES = {
    ".flac",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".ogg",
    ".wav",
    ".webm",
}


def _require_openai_key(settings: Settings) -> None:
    if not settings.openai_api_key:
        raise AppError(
            code="missing_openai_key",
            message="A chave da OpenAI não está configurada no backend. Defina OPENAI_API_KEY no .env ou no deploy.",
            status_code=503,
        )


def _client(settings: Settings) -> OpenAI:
    _require_openai_key(settings)
    return OpenAI(api_key=settings.openai_api_key)


async def transcribe_upload(file: UploadFile, settings: Optional[Settings] = None) -> str:
    settings = settings or get_settings()
    contents = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise AppError(
            code="audio_too_large",
            message=f"O áudio ultrapassa o limite de {settings.max_upload_mb} MB.",
            status_code=413,
        )

    suffix = Path(file.filename or "audio.webm").suffix.lower() or ".webm"
    if suffix not in SUPPORTED_AUDIO_SUFFIXES:
        suffix = ".webm"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(contents)
            temp_path = Path(temp_file.name)

        with temp_path.open("rb") as audio_file:
            transcription = _client(settings).audio.transcriptions.create(
                model=settings.openai_transcribe_model,
                file=audio_file,
            )
        return getattr(transcription, "text", "").strip()
    except OpenAIError as exc:
        raise AppError(
            code="transcription_failed",
            message="Não consegui transcrever o áudio agora. Tente gravar novamente ou envie em texto.",
            status_code=503,
        ) from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def synthesize_speech_base64(text: str, settings: Optional[Settings] = None) -> str:
    settings = settings or get_settings()
    if not text.strip():
        raise AppError(code="empty_tts_text", message="Não há texto para transformar em voz.", status_code=400)

    try:
        with _client(settings).audio.speech.with_streaming_response.create(
            model=settings.openai_tts_model,
            voice=settings.openai_tts_voice,
            input=text[:4096],
            response_format="mp3",
        ) as response:
            audio_bytes = response.read()
    except OpenAIError as exc:
        raise AppError(
            code="tts_failed",
            message="A resposta em texto foi gerada, mas não consegui criar o áudio agora.",
            status_code=503,
        ) from exc

    return base64.b64encode(audio_bytes).decode("ascii")
