import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Barcha sozlamalar .env yoki muhit o'zgaruvchilaridan o'qiladi."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    jwt_secret: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:5173"

    gps_radius_default_m: int = 300
    max_upload_mb: int = 10
    login_max_attempts: int = 5
    login_lock_minutes: int = 15

    static_dir: str | None = None  # demo: frontend build'i shu papkadan beriladi (bitta konteyner)
    storage_backend: str = "minio"  # "memory" — MinIO'siz lokal ishlab chiqish uchun (fayllar xotirada)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio-secret"
    minio_bucket: str = "csw-files"
    minio_secure: bool = False

    @property
    def cors_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # Render har bir servis (va PR preview) uchun o'z URL'ini beradi — Socket.IO Origin tekshiruvi uchun
        if os.getenv("RENDER_EXTERNAL_URL"):
            origins.append(os.environ["RENDER_EXTERNAL_URL"].rstrip("/"))
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
