from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Numeric, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.db import Base


class Resort(Base):
    __tablename__ = "resorts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    region: Mapped[Optional[str]] = mapped_column(String(100))
    subregion: Mapped[Optional[str]] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    elevation_base_m: Mapped[Optional[int]] = mapped_column(Integer)
    elevation_summit_m: Mapped[Optional[int]] = mapped_column(Integer)
    aspect: Mapped[Optional[str]] = mapped_column(String(20))
    vertical_drop_m: Mapped[Optional[int]] = mapped_column(Integer)
    num_runs: Mapped[Optional[int]] = mapped_column(Integer)
    season_start_month: Mapped[Optional[int]] = mapped_column(Integer)
    season_end_month: Mapped[Optional[int]] = mapped_column(Integer)
    timezone: Mapped[Optional[str]] = mapped_column(String(60))
    website_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
