"""
app/core/logging_config.py

Structured logging setup for ShopMind AI.

In development: human-readable format with timestamps and log levels.
In production: same format but WARNING+ level (less noise).

Noisy third-party loggers (httpx, SQLAlchemy engine) are silenced to keep
logs focused on application behaviour.
"""

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configure application-wide logging. Call once at startup."""
    log_level = logging.DEBUG if settings.APP_DEBUG else logging.INFO

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=fmt,
        datefmt=date_fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Third-party noise reduction
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.APP_DEBUG else logging.WARNING
    )

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured | level=%s | env=%s | mock=%s",
        logging.getLevelName(log_level),
        settings.APP_ENV,
        settings.USE_MOCK_DATA,
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper. Use in every module: logger = get_logger(__name__)"""
    return logging.getLogger(name)
