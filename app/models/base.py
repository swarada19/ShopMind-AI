"""
app/models/base.py

Shared mixins for all ORM models.

TimestampMixin adds created_at / updated_at to every table automatically.
This is standard practice — you almost always need to know when records
were created and last modified.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds created_at and updated_at columns to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def generate_uuid() -> str:
    """Generate a new UUID4 string. Used as default for primary keys."""
    return str(uuid.uuid4())
