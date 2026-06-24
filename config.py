import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _running_on_render() -> bool:
    return any(os.getenv(name) for name in ("RENDER", "RENDER_SERVICE_ID", "RENDER_EXTERNAL_HOSTNAME"))


def _is_local_origin(origin: str) -> bool:
    return origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-5.5", alias="OPENAI_CHAT_MODEL")
    openai_fast_chat_model: str = Field(default="gpt-5.4-mini", alias="OPENAI_FAST_CHAT_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-large", alias="OPENAI_EMBEDDING_MODEL")
    openai_transcribe_model: str = Field(default="whisper-1", alias="OPENAI_TRANSCRIBE_MODEL")
    openai_tts_model: str = Field(default="gpt-4o-mini-tts", alias="OPENAI_TTS_MODEL")
    openai_tts_voice: str = Field(default="alloy", alias="OPENAI_TTS_VOICE")
    realtime_enabled: bool = Field(default=False, alias="REALTIME_ENABLED")
    openai_realtime_model: str = Field(default="gpt-realtime-2", alias="OPENAI_REALTIME_MODEL")
    openai_realtime_voice: str = Field(default="cedar", alias="OPENAI_REALTIME_VOICE")
    realtime_max_session_seconds: int = Field(default=420, alias="REALTIME_MAX_SESSION_SECONDS")
    realtime_max_context_chars: int = Field(default=9000, alias="REALTIME_MAX_CONTEXT_CHARS")
    public_warmup_min_interval_seconds: int = Field(default=300, alias="PUBLIC_WARMUP_MIN_INTERVAL_SECONDS")
    openai_temperature: float = Field(default=0.1, alias="OPENAI_TEMPERATURE")
    openai_reasoning_effort: str = Field(default="low", alias="OPENAI_REASONING_EFFORT")
    openai_text_verbosity: str = Field(default="medium", alias="OPENAI_TEXT_VERBOSITY")
    openai_use_responses_api: bool = Field(default=True, alias="OPENAI_USE_RESPONSES_API")
    app_version: str = Field(default="2.2.0", alias="APP_VERSION")
    app_commit: str = Field(default="", alias="APP_COMMIT")
    app_env: str = Field(default_factory=lambda: "production" if _running_on_render() else "development", alias="APP_ENV")
    public_backend_url: str = Field(default="", alias="PUBLIC_BACKEND_URL")
    public_frontend_url: str = Field(default="", alias="PUBLIC_FRONTEND_URL")

    chroma_dir: Path = Field(default=Path("./chroma"), alias="CHROMA_DIR")
    chroma_collection: str = Field(default="gabriel_portfolio", alias="CHROMA_COLLECTION")
    data_dir: Path = Field(default=Path("./tmp"), alias="DATA_DIR")
    events_db_path: Path = Field(default=Path("./tmp/events.sqlite3"), alias="EVENTS_DB_PATH")
    database_url: str = Field(default="", alias="DATABASE_URL")
    knowledge_dir: Path = Field(default=Path("./knowledge"), alias="KNOWLEDGE_DIR")
    materials_dir: Path = Field(default=Path("./materials/recruiter-pack"), alias="MATERIALS_DIR")
    system_prompt_path: Path = Field(default=Path("./prompts/system.md"), alias="SYSTEM_PROMPT_PATH")
    rag_k: int = Field(default=8, alias="RAG_K")
    rag_lexical_k: int = Field(default=4, alias="RAG_LEXICAL_K")
    rag_max_distance: float = Field(default=1.55, alias="RAG_MAX_DISTANCE")
    rag_min_docs: int = Field(default=1, alias="RAG_MIN_DOCS")
    rag_max_context_chars: int = Field(default=14000, alias="RAG_MAX_CONTEXT_CHARS")
    rag_auto_reindex_on_missing: bool = Field(default=True, alias="RAG_AUTO_REINDEX_ON_MISSING")
    rag_auto_reindex_wait_seconds: int = Field(default=90, alias="RAG_AUTO_REINDEX_WAIT_SECONDS")
    rag_excluded_source_prefixes: str = Field(default="reports/", alias="RAG_EXCLUDED_SOURCE_PREFIXES")
    rag_trace_enabled: bool = Field(default=True, alias="RAG_TRACE_ENABLED")
    rag_feedback_enabled: bool = Field(default=True, alias="RAG_FEEDBACK_ENABLED")
    rag_suggestions_enabled: bool = Field(default=True, alias="RAG_SUGGESTIONS_ENABLED")
    rag_rerank_enabled: bool = Field(default=True, alias="RAG_RERANK_ENABLED")
    rag_rerank_provider: str = Field(default="heuristic", alias="RAG_RERANK_PROVIDER")
    rag_verifier_enabled: bool = Field(default=True, alias="RAG_VERIFIER_ENABLED")
    rag_verifier_mode: str = Field(default="async", alias="RAG_VERIFIER_MODE")
    vectorstore_backend: str = Field(default="chroma", alias="VECTORSTORE_BACKEND")
    pgvector_table: str = Field(default="rag_chunks", alias="PGVECTOR_TABLE")
    pgvector_dimension: int = Field(default=3072, alias="PGVECTOR_DIMENSION")

    frontend_origins: str = Field(
        default="https://frontend-nbecvxa81-camim2003-1759s-projects.vercel.app",
        alias="FRONTEND_ORIGINS",
    )
    allow_local_cors: bool = Field(default_factory=lambda: not _running_on_render(), alias="ALLOW_LOCAL_CORS")
    local_frontend_origin_regex: str = Field(
        default=r"^http://(localhost|127\.0\.0\.1):(5173|5174|5175|4173)$",
        alias="LOCAL_FRONTEND_ORIGIN_REGEX",
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
        origins = []
        for origin in (origin.strip().rstrip("/") for origin in self.frontend_origins.split(",") if origin.strip()):
            if not self.allow_local_cors and _is_local_origin(origin):
                continue
            origins.append(origin)
        for origin in (self.public_frontend_url, self.admin_frontend_url):
            normalized = origin.strip().rstrip("/")
            if normalized and normalized not in origins:
                origins.append(normalized)
        return origins

    @property
    def cors_allow_origin_regex(self) -> str:
        patterns = [r"https://.*\.vercel\.app"]
        if self.allow_local_cors and self.local_frontend_origin_regex.strip():
            patterns.append(self.local_frontend_origin_regex.strip())
        return "|".join(f"(?:{pattern})" for pattern in patterns)

    @property
    def admin_github_user_list(self) -> List[str]:
        return [user.strip().lower() for user in self.admin_github_users.split(",") if user.strip()]

    @property
    def rag_excluded_source_prefix_list(self) -> List[str]:
        return [prefix.strip().strip("/") + "/" for prefix in self.rag_excluded_source_prefixes.split(",") if prefix.strip()]

    @property
    def vector_backend(self) -> str:
        backend = self.vectorstore_backend.strip().lower()
        return backend if backend in {"chroma", "pgvector"} else "chroma"

    @property
    def admin_redirect_url(self) -> str:
        frontend_url = (self.public_frontend_url or self.admin_frontend_url).strip()
        if frontend_url:
            return frontend_url.rstrip("/") + "/admin"
        origins = self.frontend_origin_list
        if origins:
            return origins[0].rstrip("/") + "/admin"
        return "http://localhost:5173/admin"

    @property
    def admin_callback_base_url(self) -> str:
        backend_url = (self.public_backend_url or self.admin_public_base_url).strip()
        return backend_url.rstrip("/")

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
    def resolved_data_dir(self) -> Path:
        return self.resolve_path(self.data_dir)

    @property
    def resolved_events_db_path(self) -> Path:
        return self.resolve_path(self.events_db_path)

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
