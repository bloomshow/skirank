from __future__ import annotations
import math
import uuid
from datetime import datetime, timedelta, timezone, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.resort import Resort
from backend.models.weather import WeatherSnapshot, ForecastSnapshot
from backend.models.score import ResortScore
from backend.models.summaries import ResortSummary
from backend.schemas.responses import (
    ResortBase,
    ResortDetail,
    ResortDetailFull,
    SubScores,
    SnapshotSummary,
    ForecastDay,
    DataQualityInfo,
    DepthPoint,
    PowderIntelligence,
    RankingsInfo,
    NearbyResort,
    SummaryInfo,
)
from backend.cache import cache_get, cache_set

router = APIRouter(prefix="/resorts", tags=["resorts"])


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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


@router.get("/{slug}", response_model=ResortDetailFull)
async def get_resort(slug: str, db: AsyncSession = Depends(get_db)):
    cache_key = f"resorts:detail:v2:{slug}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Resort).where(Resort.slug == slug))
    resort = result.scalar_one_or_none()
    if not resort:
        raise HTTPException(status_code=404, detail="Resort not found")

    # ── Latest snapshot ─────────────────────────────────────────────────────
    snap_result = await db.execute(
        select(WeatherSnapshot)
        .where(WeatherSnapshot.resort_id == resort.id)
        .order_by(WeatherSnapshot.fetched_at.desc())
        .limit(1)
    )
    snapshot = snap_result.scalar_one_or_none()

    # ── Latest score at horizon 0 ────────────────────────────────────────────
    score_result = await db.execute(
        select(ResortScore)
        .where(ResortScore.resort_id == resort.id, ResortScore.horizon_days == 0)
        .order_by(ResortScore.scored_at.desc())
        .limit(1)
    )
    score = score_result.scalar_one_or_none()

    # ── 16-day forecast ──────────────────────────────────────────────────────
    forecast_result = await db.execute(
        select(ForecastSnapshot)
        .where(ForecastSnapshot.resort_id == resort.id)
        .order_by(ForecastSnapshot.forecast_date.asc())
        .limit(16)
    )
    forecast_rows = forecast_result.scalars().all()

    # ── Depth history: last 30 days (one snapshot per day) ──────────────────
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    hist_subq = (
        select(WeatherSnapshot.data_date, func.max(WeatherSnapshot.fetched_at).label("latest"))
        .where(
            WeatherSnapshot.resort_id == resort.id,
            WeatherSnapshot.fetched_at >= thirty_days_ago,
        )
        .group_by(WeatherSnapshot.data_date)
        .subquery()
    )
    hist_result = await db.execute(
        select(WeatherSnapshot.data_date, WeatherSnapshot.snow_depth_cm)
        .join(
            hist_subq,
            and_(
                WeatherSnapshot.data_date == hist_subq.c.data_date,
                WeatherSnapshot.fetched_at == hist_subq.c.latest,
            ),
        )
        .where(WeatherSnapshot.resort_id == resort.id)
        .order_by(WeatherSnapshot.data_date.asc())
    )
    depth_history = [
        DepthPoint(
            date=str(row.data_date),
            depth_cm=float(row.snow_depth_cm) if row.snow_depth_cm is not None else None,
        )
        for row in hist_result.all()
    ]

    # ── Data quality ─────────────────────────────────────────────────────────
    data_quality = None
    if snapshot:
        stale_hours = (datetime.now(timezone.utc) - snapshot.fetched_at).total_seconds() / 3600
        overall = snapshot.data_quality or "good"
        if stale_hours > 48:
            overall = "stale"
        confidence_map = {"verified": "high", "good": "medium", "suspect": "low", "unreliable": "low", "stale": "low"}
        data_quality = DataQualityInfo(
            overall=overall,
            depth_source=snapshot.source,
            depth_confidence=confidence_map.get(overall, "unknown"),
            flags=snapshot.quality_flags or [],
            last_updated=snapshot.fetched_at,
        )

    # ── Powder intelligence ──────────────────────────────────────────────────
    powder_days = [fc for fc in forecast_rows if fc.snowfall_cm and float(fc.snowfall_cm) >= 10]
    total_7d = sum(float(fc.snowfall_cm) for fc in forecast_rows[:7] if fc.snowfall_cm)
    total_14d = sum(float(fc.snowfall_cm) for fc in forecast_rows[:14] if fc.snowfall_cm)

    # Find best 3-day consecutive snowfall window
    best_window_start: Optional[date] = None
    best_window_end: Optional[date] = None
    if len(forecast_rows) >= 3:
        best_3d_total = 0.0
        for i in range(len(forecast_rows) - 2):
            window = forecast_rows[i:i + 3]
            window_total = sum(float(fc.snowfall_cm) for fc in window if fc.snowfall_cm)
            if window_total > best_3d_total:
                best_3d_total = window_total
                best_window_start = window[0].forecast_date
                best_window_end = window[-1].forecast_date

    powder_intelligence = PowderIntelligence(
        powder_days_14d=len(powder_days),
        best_window_start=str(best_window_start) if best_window_start else None,
        best_window_end=str(best_window_end) if best_window_end else None,
        total_new_snow_7d=round(total_7d, 1),
        total_new_snow_14d=round(total_14d, 1),
    )

    # ── Rankings ─────────────────────────────────────────────────────────────
    # Global: count all resorts with a score, find this resort's rank
    global_rank_result = await db.execute(
        select(ResortScore.rank_global)
        .where(ResortScore.resort_id == resort.id, ResortScore.horizon_days == 0)
        .order_by(ResortScore.scored_at.desc())
        .limit(1)
    )
    global_rank = global_rank_result.scalar_one_or_none()

    global_total_result = await db.execute(
        select(func.count()).select_from(
            select(ResortScore.resort_id)
            .where(ResortScore.horizon_days == 0)
            .group_by(ResortScore.resort_id)
            .subquery()
        )
    )
    global_total = global_total_result.scalar_one() or 0

    # Continental rank: resorts in same continent
    continental_rank: Optional[int] = None
    continental_total: Optional[int] = None
    if resort.continent:
        cont_resorts_result = await db.execute(
            select(Resort.id).where(Resort.continent == resort.continent)
        )
        cont_resort_ids = [row.id for row in cont_resorts_result.all()]
        if cont_resort_ids:
            continental_total = len(cont_resort_ids)
            cont_scores_result = await db.execute(
                select(ResortScore.resort_id, ResortScore.score_total)
                .where(
                    ResortScore.resort_id.in_(cont_resort_ids),
                    ResortScore.horizon_days == 0,
                )
                .order_by(ResortScore.scored_at.desc())
                # Get latest score per resort via distinct on resort_id
            )
            cont_scores = cont_scores_result.all()
            # Keep only latest per resort (already limited by horizon==0, take first occurrence per resort)
            seen: set = set()
            sorted_cont: list[tuple] = []
            for row in cont_scores:
                if row.resort_id not in seen:
                    seen.add(row.resort_id)
                    sorted_cont.append(row)
            sorted_cont.sort(key=lambda r: r.score_total or 0, reverse=True)
            for i, row in enumerate(sorted_cont, 1):
                if row.resort_id == resort.id:
                    continental_rank = i
                    break

    # Regional rank: resorts in same ski_region
    regional_rank: Optional[int] = None
    regional_total: Optional[int] = None
    if resort.ski_region:
        reg_resorts_result = await db.execute(
            select(Resort.id).where(Resort.ski_region == resort.ski_region)
        )
        reg_resort_ids = [row.id for row in reg_resorts_result.all()]
        if reg_resort_ids:
            regional_total = len(reg_resort_ids)
            reg_scores_result = await db.execute(
                select(ResortScore.resort_id, ResortScore.score_total)
                .where(
                    ResortScore.resort_id.in_(reg_resort_ids),
                    ResortScore.horizon_days == 0,
                )
                .order_by(ResortScore.scored_at.desc())
            )
            reg_scores = reg_scores_result.all()
            seen2: set = set()
            sorted_reg: list[tuple] = []
            for row in reg_scores:
                if row.resort_id not in seen2:
                    seen2.add(row.resort_id)
                    sorted_reg.append(row)
            sorted_reg.sort(key=lambda r: r.score_total or 0, reverse=True)
            for i, row in enumerate(sorted_reg, 1):
                if row.resort_id == resort.id:
                    regional_rank = i
                    break

    rankings_info = RankingsInfo(
        global_rank=global_rank,
        global_total=global_total,
        continental_rank=continental_rank,
        continental_total=continental_total,
        regional_rank=regional_rank,
        regional_total=regional_total,
    )

    # ── Nearby resorts (within ~300km, top 5 by score) ─────────────────────
    lat = float(resort.latitude)
    lon = float(resort.longitude)
    # Approximate bounding box: 1 degree lat ≈ 111km
    lat_delta = 3.0   # ~333km
    lon_delta = 3.0 / max(0.1, math.cos(math.radians(lat)))
    nearby_candidates_result = await db.execute(
        select(Resort)
        .where(
            Resort.id != resort.id,
            Resort.latitude.between(lat - lat_delta, lat + lat_delta),
            Resort.longitude.between(lon - lon_delta, lon + lon_delta),
        )
        .limit(30)
    )
    nearby_candidates = nearby_candidates_result.scalars().all()

    # Compute haversine distances
    nearby_with_dist = [
        (r, _haversine_km(lat, lon, float(r.latitude), float(r.longitude)))
        for r in nearby_candidates
    ]
    nearby_with_dist = [(r, d) for r, d in nearby_with_dist if d <= 300]
    nearby_with_dist.sort(key=lambda x: x[1])

    # Fetch scores for nearby resorts
    nearby_ids = [r.id for r, _ in nearby_with_dist[:10]]
    nearby_scores_map: dict = {}
    if nearby_ids:
        nearby_scores_result = await db.execute(
            select(ResortScore.resort_id, ResortScore.score_total)
            .where(ResortScore.resort_id.in_(nearby_ids), ResortScore.horizon_days == 0)
            .order_by(ResortScore.scored_at.desc())
        )
        for row in nearby_scores_result.all():
            if row.resort_id not in nearby_scores_map:
                nearby_scores_map[row.resort_id] = row.score_total

    # Fetch latest depths for nearby resorts
    nearby_depths_map: dict = {}
    if nearby_ids:
        nearby_snap_subq = (
            select(WeatherSnapshot.resort_id, func.max(WeatherSnapshot.fetched_at).label("latest"))
            .where(WeatherSnapshot.resort_id.in_(nearby_ids))
            .group_by(WeatherSnapshot.resort_id)
            .subquery()
        )
        nearby_snap_result = await db.execute(
            select(WeatherSnapshot.resort_id, WeatherSnapshot.snow_depth_cm)
            .join(
                nearby_snap_subq,
                and_(
                    WeatherSnapshot.resort_id == nearby_snap_subq.c.resort_id,
                    WeatherSnapshot.fetched_at == nearby_snap_subq.c.latest,
                ),
            )
        )
        for row in nearby_snap_result.all():
            nearby_depths_map[row.resort_id] = row.snow_depth_cm

    nearby_resorts = [
        NearbyResort(
            slug=r.slug,
            name=r.name,
            country=r.country,
            ski_region=r.ski_region,
            distance_km=round(d, 1),
            score=float(nearby_scores_map[r.id]) if r.id in nearby_scores_map else None,
            snow_depth_cm=float(nearby_depths_map[r.id]) if r.id in nearby_depths_map and nearby_depths_map[r.id] is not None else None,
        )
        for r, d in nearby_with_dist[:5]
    ]

    # ── AI Summary ───────────────────────────────────────────────────────────
    summary_info: Optional[SummaryInfo] = None
    summary_result = await db.execute(
        select(ResortSummary)
        .where(ResortSummary.resort_id == resort.id)
        .order_by(ResortSummary.valid_date.desc())
        .limit(1)
    )
    summary_row = summary_result.scalar_one_or_none()
    if summary_row:
        summary_info = SummaryInfo(
            headline=summary_row.headline or "",
            today=summary_row.summary_today or "",
            next_3d=summary_row.summary_3d or "",
            next_7d=summary_row.summary_7d or "",
            next_14d=summary_row.summary_14d or "",
            generated_at=summary_row.generated_at,
        )

    # ── Assemble response ────────────────────────────────────────────────────
    data = ResortDetailFull(
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
        data_quality=data_quality,
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
        depth_history_30d=depth_history,
        powder_intelligence=powder_intelligence,
        rankings=rankings_info,
        nearby_resorts=nearby_resorts,
        summary=summary_info,
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
