"""
app/core/config.py

Central configuration for ShopMind AI.
All settings are loaded once from .env at startup and validated by Pydantic.
Import `settings` in any module — never call os.getenv() directly.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = Field(default="ShopMind AI")
    APP_ENV: str = Field(default="development")
    APP_DEBUG: bool = Field(default=True)
    APP_VERSION: str = Field(default="1.0.0")

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(..., description="Async PostgreSQL URL")
    SYNC_DATABASE_URL: str = Field(..., description="Sync URL for Alembic migrations")

    # ── LLM: Groq ────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(..., description="Groq API key")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")

    # ── Search: SerpAPI ──────────────────────────────────────────────────────
    SERP_API_KEY: str = Field(..., description="SerpAPI key for Google Shopping")

    # ── Notifications: Twilio ────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = Field(..., description="Twilio account SID")
    TWILIO_AUTH_TOKEN: str = Field(..., description="Twilio auth token")
    TWILIO_WHATSAPP_FROM: str = Field(default="whatsapp:+14155238886")

    # ── Feature Flags ─────────────────────────────────────────────────────────
    USE_MOCK_DATA: bool = Field(
        default=False,
        description="Use mock data instead of real SerpAPI + Groq calls. "
                    "Automatically True when API keys are placeholders.",
    )
    MAX_SEARCH_RESULTS: int = Field(default=10, ge=1, le=50)

    # ── Cache ─────────────────────────────────────────────────────────────────
    PRODUCT_CACHE_TTL_HOURS: int = Field(default=6, ge=1)

    # ── Scheduler ─────────────────────────────────────────────────────────────
    ALERT_SCHEDULE_HOUR: int = Field(default=8, ge=0, le=23)
    ALERT_SCHEDULE_MINUTE: int = Field(default=0, ge=0, le=59)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "production", "testing"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}, got '{v}'")
        return v

    @field_validator("MAX_SEARCH_RESULTS")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if not (1 <= v <= 50):
            raise ValueError("MAX_SEARCH_RESULTS must be between 1 and 50")
        return v

    def model_post_init(self, __context: object) -> None:
        """Auto-enable mock mode when placeholder keys are detected."""
        placeholder_keys = {"your_groq_api_key_here", "your_serpapi_key_here", ""}
        if self.GROQ_API_KEY in placeholder_keys or self.SERP_API_KEY in placeholder_keys:
            # Use object.__setattr__ because pydantic models are frozen after init
            object.__setattr__(self, "USE_MOCK_DATA", True)

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == "testing"


settings = Settings()
