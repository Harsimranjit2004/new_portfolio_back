from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Harsimranjit Portfolio API"
    environment: str = "development"
    mongodb_uri: str = ""
    admin_api_key: str = "change-me"
    admin_username: str = "admin"
    admin_password_hash: str = ""
    cors_origins: str = "http://localhost:5173"
    public_base_url: str = "http://localhost:8000"
    storage_provider: str = "local"
    upload_dir: str = "storage"
    max_upload_mb: int = 10
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_base_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    contact_to: str = ""
    smtp_use_tls: bool = True
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 180
    rag_top_k: int = 6
    rag_min_score: float = 0.18

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
