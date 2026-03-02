from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Text, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.db import Base


class ResortSummary(Base):
    """AI-generated daily condition summaries per resort."""
    __tablename__ = "resort_summaries"
    __table_args__ = (UniqueConstraint("resort_id", "valid_date"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resorts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valid_date: Mapped[date] = mapped_column(Date, nullable=False)
    headline: Mapped[Optional[str]] = mapped_column(String(200))
    summary_today: Mapped[Optional[str]] = mapped_column(Text)
    summary_3d: Mapped[Optional[str]] = mapped_column(Text)
    summary_7d: Mapped[Optional[str]] = mapped_column(Text)
    summary_14d: Mapped[Optional[str]] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    model_version: Mapped[Optional[str]] = mapped_column(String(50), default="claude-sonnet-4-6")
