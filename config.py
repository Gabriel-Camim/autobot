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
    knowledge_dir: Path = Field(default=Path("./knowledge"), alias="KNOWLEDGE_DIR")
    materials_dir: Path = Field(default=Path("./materials/recruiter-pack"), alias="MATERIALS_DIR")
    system_prompt_path: Path = Field(default=Path("./prompts/system.md"), alias="SYSTEM_PROMPT_PATH")

    frontend_origins: str = Field(
        default="https://frontend-nbecvxa81-camim2003-1759s-projects.vercel.app",
        alias="FRONTEND_ORIGINS",
    )
    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")
    max_history_messages: int = Field(default=12, alias="MAX_HISTORY_MESSAGES")

    github_repo: str = Field(default="Gabriel-Camim/autobot", alias="GITHUB_REPO")
    github_branch: str = Field(default="main", alias="GITHUB_BRANCH")
    github_content_token: str = Field(default="", alias="GITHUB_CONTENT_TOKEN")
    github_prompt_path: str = Field(default="prompts/system.md", alias="GITHUB_PROMPT_PATH")
    github_oauth_client_id: str = Field(default="", alias="GITHUB_OAUTH_CLIENT_ID")
    github_oauth_client_secret: str = Field(default="", alias="GITHUB_OAUTH_CLIENT_SECRET")

    admin_github_users: str = Field(default="Gabriel-Camim", alias="ADMIN_GITHUB_USERS")
    admin_session_secret: str = Field(default="", alias="ADMIN_SESSION_SECRET")
    admin_public_base_url: str = Field(default="https://autobot-7hvv.onrender.com", alias="ADMIN_PUBLIC_BASE_URL")
    admin_frontend_url: str = Field(default="", alias="ADMIN_FRONTEND_URL")
    admin_cookie_name: str = Field(default="gabriel_admin_session", alias="ADMIN_COOKIE_NAME")
    admin_state_cookie_name: str = Field(default="gabriel_admin_oauth_state", alias="ADMIN_STATE_COOKIE_NAME")
    admin_cookie_samesite: str = Field(default="none", alias="ADMIN_COOKIE_SAMESITE")
    admin_cookie_secure: bool = Field(default=True, alias="ADMIN_COOKIE_SECURE")
    admin_session_hours: int = Field(default=8, alias="ADMIN_SESSION_HOURS")

    @property
    def frontend_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def admin_github_user_list(self) -> List[str]:
        return [user.strip().lower() for user in self.admin_github_users.split(",") if user.strip()]

    @property
    def admin_redirect_url(self) -> str:
        if self.admin_frontend_url:
            return self.admin_frontend_url.rstrip("/") + "/admin"
        origins = self.frontend_origin_list
        if origins:
            return origins[0].rstrip("/") + "/admin"
        return "http://localhost:5173/admin"

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

    @property
    def resolved_system_prompt_path(self) -> Path:
        return self.resolve_path(self.system_prompt_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
