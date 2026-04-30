"""
Stock360 AI — Application Configuration
All secrets via environment variables. Never hardcode credentials.
"""
import json
import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "Stock360 AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development | staging | production

    # ── Security ─────────────────────────────────────────────────────────
    SECRET_KEY: str = secrets.token_urlsafe(64)   # override in .env!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://stock360:password@db:5432/stock360"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── AI ───────────────────────────────────────────────────────────────
    AI_PROVIDER: str = "demo"  # anthropic | ollama | demo
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-20250514"
    AI_MAX_TOKENS: int = 1024
    AI_TEMPERATURE: float = 0.7
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # ── Stripe ───────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_SUCCESS_URL: str = "http://localhost:3000/payment-success"

    # ── CORS ─────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://yourdomain.com"

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    AI_RATE_LIMIT_PER_MINUTE: int = 20

    # ── WhatsApp (Meta Cloud API) ─────────────────────────────────────────
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = secrets.token_urlsafe(32)

    # ── Facebook Messenger ────────────────────────────────────────────────
    MESSENGER_PAGE_TOKEN: str = ""
    MESSENGER_VERIFY_TOKEN: str = secrets.token_urlsafe(32)

    # ── Email (notifications) ────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@stock360.ai"

    # ── Admin seed ───────────────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@stock360.ai"
    ADMIN_PASSWORD: str = "ChangeMe123!"   # MUST change on first deploy

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

    @property
    def allowed_origins_list(self) -> list[str]:
        raw = self.ALLOWED_ORIGINS.strip()
        if not raw:
            return []
        if raw.startswith("["):
            return [origin.strip() for origin in json.loads(raw) if origin.strip()]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
