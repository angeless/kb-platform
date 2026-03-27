"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "change-me-in-production"
_DEFAULT_ENCRYPTION_KEY = "change-me-32-byte-key-for-aes256"
_DEFAULT_POSTGRES_PASSWORD = "postgres"
_DEFAULT_MINIO_KEY = "minioadmin"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "kb-platform"
    app_port: int = 8080
    debug: bool = False

    # Environment (development / staging / production)
    environment: str = "development"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "kb_platform"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # MinIO / S3
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "kb-assets"
    s3_region: str = "us-east-1"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Encryption
    encryption_key: str = "change-me-32-byte-key-for-aes256"

    # Rate Limiting
    rate_limit_per_minute: int = 100
    upload_rate_limit_per_minute: int = 20

    # Upload
    max_upload_size_mb: int = 100

    # Auth rate limiting (stricter than general rate limits)
    auth_login_rate_limit: int = 10
    auth_register_rate_limit: int = 5
    auth_refresh_rate_limit: int = 30

    # Logging
    log_level: str = "INFO"

    # SMTP (email)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@kb-platform.com"
    smtp_tls: bool = True

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Reject default secrets in production environment."""
        if self.environment == "production":
            if self.jwt_secret == _DEFAULT_JWT_SECRET:
                raise ValueError(
                    "jwt_secret must not use default value in production. "
                    "Set JWT_SECRET environment variable."
                )
            if self.encryption_key == _DEFAULT_ENCRYPTION_KEY:
                raise ValueError(
                    "encryption_key must not use default value in production. "
                    "Set ENCRYPTION_KEY environment variable."
                )
            if len(self.jwt_secret) < 32:
                raise ValueError(
                    "jwt_secret must be at least 32 characters in production."
                )
            if len(self.encryption_key) < 32:
                raise ValueError(
                    "encryption_key must be at least 32 characters in production."
                )
            if self.postgres_password == _DEFAULT_POSTGRES_PASSWORD:
                raise ValueError(
                    "postgres_password must not use default 'postgres' in production. "
                    "Set POSTGRES_PASSWORD environment variable."
                )
            if self.s3_access_key == _DEFAULT_MINIO_KEY or self.s3_secret_key == _DEFAULT_MINIO_KEY:
                raise ValueError(
                    "s3_access_key/s3_secret_key must not use default 'minioadmin' in production. "
                    "Set S3_ACCESS_KEY and S3_SECRET_KEY environment variables."
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
