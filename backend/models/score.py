from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.db import Base


class ResortScore(Base):
    __tablename__ = "resort_scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resorts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    score_total: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    score_base_depth: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    score_fresh_snow: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    score_temperature: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    score_wind: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    score_forecast: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    rank_global: Mapped[Optional[int]] = mapped_column(Integer)
    rank_regional: Mapped[Optional[int]] = mapped_column(Integer)
