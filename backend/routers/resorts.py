from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.resort import Resort
from backend.models.weather import WeatherSnapshot, ForecastSnapshot
from backend.models.score import ResortScore
from backend.schemas.responses import (
    ResortBase,
    ResortDetail,
    SubScores,
    SnapshotSummary,
    ForecastDay,
)
from backend.cache import cache_get, cache_set

router = APIRouter(prefix="/resorts", tags=["resorts"])


@router.get("", response_model=list[ResortBase])
async def list_resorts(
    region: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"resorts:list:{region}:{country}:{search}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    stmt = select(Resort)
    if region:
        stmt = stmt.where(Resort.region.ilike(f"%{region}%"))
    if country:
        stmt = stmt.where(Resort.country == country.upper())
    if search:
        stmt = stmt.where(Resort.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Resort.name)

    result = await db.execute(stmt)
    resorts = result.scalars().all()
    data = [ResortBase.model_validate(r).model_dump(mode="json") for r in resorts]
    await cache_set(cache_key, data, ttl_seconds=3600)
    return data


@router.get("/{slug}", response_model=ResortDetail)
async def get_resort(slug: str, db: AsyncSession = Depends(get_db)):
    cache_key = f"resorts:detail:{slug}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Resort).where(Resort.slug == slug))
    resort = result.scalar_one_or_none()
    if not resort:
        raise HTTPException(status_code=404, detail="Resort not found")

    # Latest snapshot
    snap_result = await db.execute(
        select(WeatherSnapshot)
        .where(WeatherSnapshot.resort_id == resort.id)
        .order_by(WeatherSnapshot.fetched_at.desc())
        .limit(1)
    )
    snapshot = snap_result.scalar_one_or_none()

    # Latest score (horizon 0)
    score_result = await db.execute(
        select(ResortScore)
        .where(ResortScore.resort_id == resort.id, ResortScore.horizon_days == 0)
        .order_by(ResortScore.scored_at.desc())
        .limit(1)
    )
    score = score_result.scalar_one_or_none()

    # 16-day forecast
    forecast_result = await db.execute(
        select(ForecastSnapshot)
        .where(ForecastSnapshot.resort_id == resort.id)
        .order_by(ForecastSnapshot.forecast_date.asc())
        .limit(16)
    )
    forecast_rows = forecast_result.scalars().all()

    data = ResortDetail(
        resort=ResortBase.model_validate(resort),
        current_score=float(score.score_total) if score and score.score_total else None,
        sub_scores=SubScores(
            base_depth=float(score.score_base_depth) if score and score.score_base_depth else None,
            fresh_snow=float(score.score_fresh_snow) if score and score.score_fresh_snow else None,
            temperature=float(score.score_temperature) if score and score.score_temperature else None,
            wind=float(score.score_wind) if score and score.score_wind else None,
            forecast=float(score.score_forecast) if score and score.score_forecast else None,
        ),
        snapshot=SnapshotSummary(
            snow_depth_cm=float(snapshot.snow_depth_cm) if snapshot and snapshot.snow_depth_cm else None,
            new_snow_72h_cm=float(snapshot.new_snow_72h_cm) if snapshot and snapshot.new_snow_72h_cm else None,
            temperature_c=float(snapshot.temperature_c) if snapshot and snapshot.temperature_c else None,
            wind_speed_kmh=float(snapshot.wind_speed_kmh) if snapshot and snapshot.wind_speed_kmh else None,
        ),
        forecast=[
            ForecastDay(
                forecast_date=f.forecast_date,
                snowfall_cm=float(f.snowfall_cm) if f.snowfall_cm else None,
                temperature_max_c=float(f.temperature_max_c) if f.temperature_max_c else None,
                temperature_min_c=float(f.temperature_min_c) if f.temperature_min_c else None,
                wind_speed_max_kmh=float(f.wind_speed_max_kmh) if f.wind_speed_max_kmh else None,
                precipitation_prob_pct=f.precipitation_prob_pct,
                weather_code=f.weather_code,
                confidence_score=float(f.confidence_score) if f.confidence_score else None,
            )
            for f in forecast_rows
        ],
    )
    await cache_set(cache_key, data.model_dump(mode="json"), ttl_seconds=3600)
    return data


@router.get("/{slug}/forecast", response_model=list[ForecastDay])
async def get_resort_forecast(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resort).where(Resort.slug == slug))
    resort = result.scalar_one_or_none()
    if not resort:
        raise HTTPException(status_code=404, detail="Resort not found")

    forecast_result = await db.execute(
        select(ForecastSnapshot)
        .where(ForecastSnapshot.resort_id == resort.id)
        .order_by(ForecastSnapshot.forecast_date.asc())
        .limit(16)
    )
    return [
        ForecastDay(
            forecast_date=f.forecast_date,
            snowfall_cm=float(f.snowfall_cm) if f.snowfall_cm else None,
            temperature_max_c=float(f.temperature_max_c) if f.temperature_max_c else None,
            temperature_min_c=float(f.temperature_min_c) if f.temperature_min_c else None,
            wind_speed_max_kmh=float(f.wind_speed_max_kmh) if f.wind_speed_max_kmh else None,
            precipitation_prob_pct=f.precipitation_prob_pct,
            weather_code=f.weather_code,
            confidence_score=float(f.confidence_score) if f.confidence_score else None,
        )
        for f in forecast_result.scalars().all()
    ]
