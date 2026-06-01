"""
tests/test_config.py

Verifies that the settings object loads and validates correctly.

Run with:
    pytest tests/test_config.py -v
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings


class TestSettings:
    def test_settings_loads_from_env(self):
        """The global settings object should load without error."""
        assert settings.APP_NAME == "ShopMind AI"
        assert settings.APP_ENV == "development"
        assert settings.GROQ_MODEL == "llama-3.3-70b-versatile"

    def test_is_development_property(self):
        """is_development should return True when APP_ENV=development."""
        assert settings.is_development is True
        assert settings.is_production is False

    def test_invalid_app_env_raises(self):
        """APP_ENV must be one of: development, production, testing."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="staging",                     # invalid
                DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
                SYNC_DATABASE_URL="postgresql+psycopg2://u:p@localhost/db",
                GROQ_API_KEY="fake",
                SERP_API_KEY="fake",
                TWILIO_ACCOUNT_SID="fake",
                TWILIO_AUTH_TOKEN="fake",
            )
        assert "APP_ENV" in str(exc_info.value)

    def test_cache_ttl_has_sensible_default(self):
        """Cache TTL should default to 6 hours."""
        assert settings.PRODUCT_CACHE_TTL_HOURS == 6
