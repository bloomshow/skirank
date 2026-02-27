from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.db import Base


class ResortDepthOverride(Base):
    """
    Manually set base depth for a resort.

    Overrides the pipeline's fetched depth each day until cumulative new snow
    since the override was set exceeds new_snow_threshold_cm, at which point
    the override auto-expires and the pipeline resumes using live data.
    """
    __tablename__ = "resort_depth_overrides"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resorts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one override record per resort (upserted in-place)
    )
    override_depth_cm: Mapped[float] = mapped_column(Numeric(6, 1), nullable=False)
    override_reason: Mapped[Optional[str]] = mapped_column(String(500))
    override_set_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    cumulative_new_snow_since_cm: Mapped[float] = mapped_column(
        Numeric(6, 1), default=0.0, nullable=False
    )
    new_snow_threshold_cm: Mapped[float] = mapped_column(
        Numeric(6, 1), default=20.0, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
