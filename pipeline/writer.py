"""
Database writer for the SkiRank pipeline.

Takes the output of fetcher.py and scorer.py and persists it to PostgreSQL.
Handles per-resort failure isolation — one resort failure does not abort the run.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pipeline.config import DATABASE_URL
from pipeline.fetcher import ResortWeatherData
from pipeline.scorer import ScoreResult

logger = logging.getLogger(__name__)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def write_weather_snapshots(
    session: AsyncSession,
    weather_data: list[ResortWeatherData],
    today: date,
) -> tuple[int, int]:
    """
    Upsert weather snapshots and forecast snapshots for today's pipeline run.

    Returns (success_count, failure_count).
    """
    from backend.models.weather import WeatherSnapshot, ForecastSnapshot

    success = 0
    failures = 0

    for data in weather_data:
        try:
            resort_uuid = uuid.UUID(str(data.resort_id))

            # Replace today's snapshot (delete then insert to keep one row per resort per day)
            await session.execute(
                delete(WeatherSnapshot).where(
                    WeatherSnapshot.resort_id == resort_uuid,
                    WeatherSnapshot.data_date == today,
                )
            )
            snapshot = WeatherSnapshot(
                id=uuid.uuid4(),
                resort_id=resort_uuid,
                fetched_at=data.fetched_at,
                data_date=today,
                snow_depth_cm=data.snow_depth_cm,
                new_snow_24h_cm=data.new_snow_24h_cm,
                new_snow_72h_cm=data.new_snow_72h_cm,
                temperature_c=data.temperature_c,
                wind_speed_kmh=data.wind_speed_kmh,
                weather_code=data.weather_code,
                source="open_meteo",
            )
            session.add(snapshot)

            # Delete old forecasts for this resort (keep today's run only)
            await session.execute(
                delete(ForecastSnapshot).where(ForecastSnapshot.resort_id == resort_uuid)
            )

            for fc in data.forecasts:
                forecast = ForecastSnapshot(
                    id=uuid.uuid4(),
                    resort_id=resort_uuid,
                    fetched_at=data.fetched_at,
                    forecast_date=fc.forecast_date,
                    snowfall_cm=fc.snowfall_cm,
                    temperature_max_c=fc.temperature_max_c,
                    temperature_min_c=fc.temperature_min_c,
                    wind_speed_max_kmh=fc.wind_speed_max_kmh,
                    precipitation_prob_pct=fc.precipitation_prob_pct,
                    weather_code=fc.weather_code,
                    confidence_score=fc.confidence_score,
                )
                session.add(forecast)

            success += 1
        except Exception as exc:
            logger.error("Failed to write weather data for resort %s: %s", data.resort_id, exc)
            failures += 1

    await session.commit()
    return success, failures


async def write_scores(
    session: AsyncSession,
    resort_id: str,
    scores_by_horizon: dict[int, ScoreResult],
    scored_at: datetime,
) -> None:
    """Write computed scores for a single resort across all horizons."""
    from backend.models.score import ResortScore

    resort_uuid = uuid.UUID(str(resort_id))

    for horizon_days, result in scores_by_horizon.items():
        # Replace existing score for this resort+horizon (one row per resort per horizon)
        await session.execute(
            delete(ResortScore).where(
                ResortScore.resort_id == resort_uuid,
                ResortScore.horizon_days == horizon_days,
            )
        )
        score = ResortScore(
            id=uuid.uuid4(),
            resort_id=resort_uuid,
            scored_at=scored_at,
            horizon_days=horizon_days,
            score_total=result.score_total,
            score_base_depth=result.score_base_depth,
            score_fresh_snow=result.score_fresh_snow,
            score_temperature=result.score_temperature,
            score_wind=result.score_wind,
            score_forecast=result.score_forecast,
        )
        session.add(score)

    await session.commit()


async def update_global_ranks(session: AsyncSession, horizon_days: int, scored_at: datetime) -> None:
    """
    Assign rank_global to the latest scores for a given horizon.
    Uses a simple Python sort — for scale, this should become a DB window function.
    """
    from backend.models.score import ResortScore
    from sqlalchemy import func, and_

    subq = (
        select(
            ResortScore.resort_id,
            func.max(ResortScore.scored_at).label("latest"),
        )
        .where(ResortScore.horizon_days == horizon_days)
        .group_by(ResortScore.resort_id)
        .subquery()
    )

    result = await session.execute(
        select(ResortScore)
        .join(
            subq,
            and_(
                ResortScore.resort_id == subq.c.resort_id,
                ResortScore.scored_at == subq.c.latest,
            ),
        )
        .where(ResortScore.horizon_days == horizon_days)
        .order_by(ResortScore.score_total.desc().nullslast())
    )
    scores = result.scalars().all()

    for rank, score in enumerate(scores, start=1):
        score.rank_global = rank

    await session.commit()
