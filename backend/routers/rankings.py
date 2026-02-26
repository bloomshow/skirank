from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date as date_type
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.resort import Resort
from backend.models.weather import WeatherSnapshot, ForecastSnapshot
from backend.models.score import ResortScore
from backend.schemas.responses import (
    RankingsResponse,
    RankingsMeta,
    RankingEntry,
    ResortBase,
    SubScores,
    SnapshotSummary,
    ForecastSnowDay,
)
from backend.cache import cache_get, cache_set

router = APIRouter(prefix="/rankings", tags=["rankings"])

DEFAULT_WEIGHTS = {
    "base_depth": 0.25,
    "fresh_snow": 0.35,
    "temperature": 0.20,
    "wind": 0.10,
    "forecast": 0.10,
}


def _recompute_score(score: ResortScore, weights: dict[str, float]) -> float:
    """Recompute composite score with custom weights (weights must sum to 1.0)."""
    total = weights.get("base_depth", 0) * (float(score.score_base_depth) if score.score_base_depth else 0)
    total += weights.get("fresh_snow", 0) * (float(score.score_fresh_snow) if score.score_fresh_snow else 0)
    total += weights.get("temperature", 0) * (float(score.score_temperature) if score.score_temperature else 0)
    total += weights.get("wind", 0) * (float(score.score_wind) if score.score_wind else 0)
    total += weights.get("forecast", 0) * (float(score.score_forecast) if score.score_forecast else 0)
    return round(total, 1)


SLUG_TO_CONTINENT = {
    "north-america": "North America",
    "europe": "Europe",
    "asia": "Asia",
    "south-america": "South America",
    "oceania": "Oceania",
}

SLUG_TO_SKI_REGION = {
    "colorado": "Colorado", "utah": "Utah", "california": "California",
    "pacific-northwest": "Pacific Northwest", "mountain-west": "Mountain West",
    "northeast-usa": "Northeast USA", "british-columbia": "British Columbia",
    "alberta": "Alberta", "eastern-canada": "Eastern Canada",
    "french-alps": "French Alps", "swiss-alps": "Swiss Alps",
    "austrian-alps": "Austrian Alps", "italian-alps": "Italian Alps",
    "scandinavia": "Scandinavia", "pyrenees-and-iberia": "Pyrenees & Iberia",
    "hokkaido": "Hokkaido", "honshu": "Honshu",
    "andes": "Andes", "australian-alps": "Australian Alps",
    "southern-alps": "Southern Alps",
}


@router.get("", response_model=RankingsResponse)
async def get_rankings(
    horizon_days: int = Query(0, ge=0, le=14),
    region: List[str] = Query(default=[]),
    subregion: List[str] = Query(default=[]),
    country: List[str] = Query(default=[]),
    continent: Optional[str] = Query(None),
    ski_region: List[str] = Query(default=[]),
    min_elevation_m: Optional[int] = Query(None),
    sort: str = Query("score", pattern="^(score|predicted_snow)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    w_base_depth: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_fresh_snow: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_temperature: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_wind: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    custom_weights = any(w is not None for w in [w_base_depth, w_fresh_snow, w_temperature, w_wind])
    has_hierarchy_filters = bool(continent or ski_region or country)

    # Only use cache for default weights, no filters, default sort
    use_cache = (
        not custom_weights
        and not region
        and not subregion
        and not has_hierarchy_filters
        and not min_elevation_m
        and sort == "score"
    )
    cache_key = f"rankings:{horizon_days}:{page}:{per_page}"
    if use_cache:
        cached = await cache_get(cache_key)
        if cached:
            return cached

    # Build weights dict
    if custom_weights:
        raw = {
            "base_depth": w_base_depth if w_base_depth is not None else DEFAULT_WEIGHTS["base_depth"],
            "fresh_snow": w_fresh_snow if w_fresh_snow is not None else DEFAULT_WEIGHTS["fresh_snow"],
            "temperature": w_temperature if w_temperature is not None else DEFAULT_WEIGHTS["temperature"],
            "wind": w_wind if w_wind is not None else DEFAULT_WEIGHTS["wind"],
        }
        total_w = sum(raw.values())
        if total_w > 0:
            weights = {k: v / total_w for k, v in raw.items()}
            weights["forecast"] = 0.0
        else:
            weights = DEFAULT_WEIGHTS
    else:
        weights = DEFAULT_WEIGHTS

    # 7-day forecast window for predicted snow
    today = date_type.today()
    seven_days = today + timedelta(days=7)

    # Subquery: sum of predicted snowfall per resort over next 7 days
    snow_subq = (
        select(
            ForecastSnapshot.resort_id,
            func.sum(ForecastSnapshot.snowfall_cm).label("predicted_snow_cm"),
        )
        .where(
            ForecastSnapshot.forecast_date >= today,
            ForecastSnapshot.forecast_date < seven_days,
        )
        .group_by(ForecastSnapshot.resort_id)
        .subquery()
    )

    # Subquery: forecast_source — 'nws_hrrr' if any upcoming forecast has that source, else 'open_meteo'
    # func.min() returns 'nws_hrrr' if present ('n' < 'o' alphabetically)
    forecast_src_subq = (
        select(
            ForecastSnapshot.resort_id,
            func.min(ForecastSnapshot.source).label("forecast_source"),
        )
        .where(
            ForecastSnapshot.forecast_date >= today,
            ForecastSnapshot.forecast_date < seven_days,
        )
        .group_by(ForecastSnapshot.resort_id)
        .subquery()
    )

    # Get latest scores for the given horizon
    subq = (
        select(
            ResortScore.resort_id,
            func.max(ResortScore.scored_at).label("latest_scored_at"),
        )
        .where(ResortScore.horizon_days == horizon_days)
        .group_by(ResortScore.resort_id)
        .subquery()
    )

    # Get latest weather snapshot per resort
    snap_subq = (
        select(
            WeatherSnapshot.resort_id,
            func.max(WeatherSnapshot.fetched_at).label("latest_fetched_at"),
        )
        .group_by(WeatherSnapshot.resort_id)
        .subquery()
    )

    stmt = (
        select(
            Resort,
            ResortScore,
            WeatherSnapshot,
            snow_subq.c.predicted_snow_cm,
            forecast_src_subq.c.forecast_source,
        )
        .join(subq, Resort.id == subq.c.resort_id)
        .join(
            ResortScore,
            and_(
                ResortScore.resort_id == Resort.id,
                ResortScore.scored_at == subq.c.latest_scored_at,
                ResortScore.horizon_days == horizon_days,
            ),
        )
        .outerjoin(snap_subq, snap_subq.c.resort_id == Resort.id)
        .outerjoin(
            WeatherSnapshot,
            and_(
                WeatherSnapshot.resort_id == Resort.id,
                WeatherSnapshot.fetched_at == snap_subq.c.latest_fetched_at,
            ),
        )
        .outerjoin(snow_subq, snow_subq.c.resort_id == Resort.id)
        .outerjoin(forecast_src_subq, forecast_src_subq.c.resort_id == Resort.id)
    )

    if region:
        stmt = stmt.where(Resort.region.in_(region))
    if subregion:
        stmt = stmt.where(Resort.subregion.in_(subregion))
    if continent:
        cont_label = SLUG_TO_CONTINENT.get(continent)
        if cont_label:
            stmt = stmt.where(Resort.continent == cont_label)
    if ski_region:
        sr_labels = [SLUG_TO_SKI_REGION.get(s, s) for s in ski_region]
        stmt = stmt.where(Resort.ski_region.in_(sr_labels))
    if country:
        stmt = stmt.where(Resort.country.in_([c.upper() for c in country]))
    if min_elevation_m:
        stmt = stmt.where(Resort.elevation_summit_m >= min_elevation_m)

    # Count total before pagination
    count_result = await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total = count_result.scalar_one()

    # Apply sorting and pagination
    if sort == "predicted_snow":
        stmt = stmt.order_by(snow_subq.c.predicted_snow_cm.desc().nullslast())
    else:
        stmt = stmt.order_by(ResortScore.score_total.desc().nullslast())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)

    rows = (await db.execute(stmt)).all()

    # Batch-fetch sparkline data for all resorts on this page
    resort_ids = [row[0].id for row in rows]
    sparklines: dict = defaultdict(list)
    if resort_ids:
        sparkline_result = await db.execute(
            select(
                ForecastSnapshot.resort_id,
                ForecastSnapshot.forecast_date,
                ForecastSnapshot.snowfall_cm,
            )
            .where(
                ForecastSnapshot.resort_id.in_(resort_ids),
                ForecastSnapshot.forecast_date >= today,
                ForecastSnapshot.forecast_date < seven_days,
            )
            .order_by(ForecastSnapshot.resort_id, ForecastSnapshot.forecast_date)
        )
        for sl_row in sparkline_result.all():
            sparklines[sl_row.resort_id].append(
                ForecastSnowDay(
                    date=sl_row.forecast_date.isoformat(),
                    snowfall_cm=float(sl_row.snowfall_cm) if sl_row.snowfall_cm is not None else None,
                )
            )

    stale_threshold = datetime.now(timezone.utc) - timedelta(hours=48)

    results = []
    for rank_offset, row in enumerate(rows, start=(page - 1) * per_page + 1):
        resort, score, snapshot, predicted_snow_cm, forecast_source = (
            row[0], row[1], row[2], row[3], row[4]
        )
        depth_source = snapshot.source if snapshot else None
        computed_score = _recompute_score(score, weights) if custom_weights else (
            float(score.score_total) if score.score_total else None
        )
        stale = snapshot is None or snapshot.fetched_at < stale_threshold if snapshot else True

        results.append(
            RankingEntry(
                rank=rank_offset,
                resort=ResortBase.model_validate(resort),
                score=computed_score,
                sub_scores=SubScores(
                    base_depth=float(score.score_base_depth) if score.score_base_depth else None,
                    fresh_snow=float(score.score_fresh_snow) if score.score_fresh_snow else None,
                    temperature=float(score.score_temperature) if score.score_temperature else None,
                    wind=float(score.score_wind) if score.score_wind else None,
                    forecast=float(score.score_forecast) if score.score_forecast else None,
                ),
                snapshot=SnapshotSummary(
                    snow_depth_cm=float(snapshot.snow_depth_cm) if snapshot and snapshot.snow_depth_cm else None,
                    new_snow_72h_cm=float(snapshot.new_snow_72h_cm) if snapshot and snapshot.new_snow_72h_cm else None,
                    temperature_c=float(snapshot.temperature_c) if snapshot and snapshot.temperature_c else None,
                    wind_speed_kmh=float(snapshot.wind_speed_kmh) if snapshot and snapshot.wind_speed_kmh else None,
                ),
                stale_data=stale,
                predicted_snow_cm=float(predicted_snow_cm) if predicted_snow_cm is not None else None,
                forecast_sparkline=sparklines.get(resort.id, []),
                forecast_source=forecast_source,
                depth_source=depth_source,
            )
        )

    response = RankingsResponse(
        meta=RankingsMeta(
            total=total,
            page=page,
            per_page=per_page,
            horizon_days=horizon_days,
        ),
        generated_at=datetime.now(timezone.utc),
        results=results,
    )

    if use_cache:
        await cache_set(cache_key, response.model_dump(mode="json"), ttl_seconds=3600)

    return response


@router.get("/map", response_model=list[dict])
async def get_rankings_map(
    horizon_days: int = Query(0, ge=0, le=14),
    db: AsyncSession = Depends(get_db),
):
    """All resorts with lat/lng + score for map display."""
    cache_key = f"rankings:map:{horizon_days}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    subq = (
        select(
            ResortScore.resort_id,
            func.max(ResortScore.scored_at).label("latest"),
        )
        .where(ResortScore.horizon_days == horizon_days)
        .group_by(ResortScore.resort_id)
        .subquery()
    )

    stmt = (
        select(Resort, ResortScore)
        .join(subq, Resort.id == subq.c.resort_id)
        .join(
            ResortScore,
            and_(
                ResortScore.resort_id == Resort.id,
                ResortScore.scored_at == subq.c.latest,
                ResortScore.horizon_days == horizon_days,
            ),
        )
    )

    rows = (await db.execute(stmt)).all()
    data = [
        {
            "slug": r.slug,
            "name": r.name,
            "latitude": float(r.latitude),
            "longitude": float(r.longitude),
            "region": r.region,
            "score": float(s.score_total) if s.score_total else None,
        }
        for r, s in rows
    ]
    await cache_set(cache_key, data, ttl_seconds=3600)
    return data
