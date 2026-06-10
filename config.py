from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-4o", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    openai_transcribe_model: str = Field(default="whisper-1", alias="OPENAI_TRANSCRIBE_MODEL")
    openai_tts_model: str = Field(default="gpt-4o-mini-tts", alias="OPENAI_TTS_MODEL")
    openai_tts_voice: str = Field(default="alloy", alias="OPENAI_TTS_VOICE")

    chroma_dir: Path = Field(default=Path("./chroma"), alias="CHROMA_DIR")
    chroma_collection: str = Field(default="gabriel_portfolio", alias="CHROMA_COLLECTION")
    knowledge_dir: Path = Field(default=Path("../knowledge"), alias="KNOWLEDGE_DIR")
    materials_dir: Path = Field(default=Path("../materials/recruiter-pack"), alias="MATERIALS_DIR")

    frontend_origins: str = Field(
        default="https://frontend-nbecvxa81-camim2003-1759s-projects.vercel.app",
        alias="FRONTEND_ORIGINS",
    )
    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")
    max_history_messages: int = Field(default=12, alias="MAX_HISTORY_MESSAGES")

    @property
    def frontend_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def backend_dir(self) -> Path:
        return Path(__file__).resolve().parent

    @property
    def project_root(self) -> Path:
        return self.backend_dir.parent

    def resolve_path(self, value: Path) -> Path:
        if value.is_absolute():
            return value.resolve()
        return (self.backend_dir / value).resolve()

    @property
    def resolved_chroma_dir(self) -> Path:
        return self.resolve_path(self.chroma_dir)

    @property
    def resolved_knowledge_dir(self) -> Path:
        return self.resolve_path(self.knowledge_dir)

    @property
    def resolved_materials_dir(self) -> Path:
        return self.resolve_path(self.materials_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
