from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Numeric, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.db import Base


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resorts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_date: Mapped[date] = mapped_column(Date, nullable=False)
    snow_depth_cm: Mapped[Optional[float]] = mapped_column(Numeric(6, 1))
    new_snow_24h_cm: Mapped[Optional[float]] = mapped_column(Numeric(6, 1))
    new_snow_72h_cm: Mapped[Optional[float]] = mapped_column(Numeric(6, 1))
    temperature_c: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    wind_speed_kmh: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    visibility_km: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    weather_code: Mapped[Optional[int]] = mapped_column(Integer)
    source: Mapped[Optional[str]] = mapped_column(String(50))


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resorts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    snowfall_cm: Mapped[Optional[float]] = mapped_column(Numeric(6, 1))
    temperature_max_c: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    temperature_min_c: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    wind_speed_max_kmh: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    precipitation_prob_pct: Mapped[Optional[int]] = mapped_column(Integer)
    weather_code: Mapped[Optional[int]] = mapped_column(Integer)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
