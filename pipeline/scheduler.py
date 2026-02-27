"""
APScheduler job definition for the SkiRank daily pipeline.

Runs fetch → score → write → rank at 06:00 UTC daily.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from pipeline.config import PIPELINE_CRON_SCHEDULE, SCORE_HORIZONS
from pipeline.fetcher import fetch_all_resorts
from pipeline.validator import run_validation
from pipeline.scorer import (
    compute_score,
    CurrentConditions,
    ForecastDay as ScorerForecastDay,
    ResortMeta,
)
from pipeline.writer import SessionLocal, write_weather_snapshots, write_scores, update_global_ranks

logger = logging.getLogger(__name__)


async def run_pipeline() -> None:
    logger.info("Pipeline started at %s", datetime.now(timezone.utc).isoformat())
    today = date.today()

    async with SessionLocal() as session:
        from sqlalchemy import select
        from backend.models.resort import Resort

        result = await session.execute(
            select(
                Resort.id,
                Resort.slug,
                Resort.country,
                Resort.latitude,
                Resort.longitude,
                Resort.elevation_summit_m,
                Resort.aspect,
                Resort.season_start_month,
                Resort.season_end_month,
                Resort.region,
            )
        )
        resorts = [
            {
                "id": str(row.id),
                "slug": row.slug,
                "country": row.country,
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "elevation_summit_m": row.elevation_summit_m,
                "aspect": row.aspect,
                "season_start_month": row.season_start_month,
                "season_end_month": row.season_end_month,
                "region": row.region,
            }
            for row in result.all()
        ]

    if not resorts:
        logger.warning("No resorts found in database — skipping pipeline run.")
        return

    logger.info("Fetching weather for %d resorts...", len(resorts))
    weather_results, failed_ids = await fetch_all_resorts(resorts)

    # Build a lookup for resort metadata (used for station override, validation, and scoring)
    resort_meta_map = {r["id"]: r for r in resorts}

    # Query previous depths from DB before writing today's snapshots
    previous_depths: dict[str, float] = {}
    async with SessionLocal() as session:
        from sqlalchemy import func as _func, and_ as _and_
        from backend.models.weather import WeatherSnapshot as _WS
        prev_subq = (
            select(_WS.resort_id, _func.max(_WS.fetched_at).label("latest"))
            .group_by(_WS.resort_id)
            .subquery()
        )
        prev_result = await session.execute(
            select(_WS.resort_id, _WS.snow_depth_cm)
            .join(prev_subq, _and_(
                _WS.resort_id == prev_subq.c.resort_id,
                _WS.fetched_at == prev_subq.c.latest,
            ))
        )
        for row in prev_result.all():
            if row.snow_depth_cm is not None:
                previous_depths[str(row.resort_id)] = float(row.snow_depth_cm)

    # Enrich snow depth from on-mountain stations for all resorts (overrides Open-Meteo grid estimate)
    from pipeline.station_fetcher import fetch_station_depths
    all_slugs = [r["slug"] for r in resorts]
    station_readings = await fetch_station_depths(all_slugs)

    for weather in weather_results:
        resort = resort_meta_map.get(weather.resort_id, {})
        slug = resort.get("slug")
        # openmeteo_depth_cm is already set from the fetcher; station override only changes snow_depth_cm
        if slug and slug in station_readings:
            weather.snow_depth_cm = station_readings[slug].snow_depth_cm
            weather.depth_source = "synoptic_station"
            logger.info(
                "Station override for %s: %.1f cm (stid=%s, date=%s)",
                slug,
                weather.snow_depth_cm,
                station_readings[slug].stid,
                station_readings[slug].data_date,
            )

    # Apply manual depth overrides — takes precedence over station data
    from sqlalchemy import update as _update
    from backend.models.overrides import ResortDepthOverride

    async with SessionLocal() as session:
        ov_result = await session.execute(
            select(ResortDepthOverride).where(ResortDepthOverride.is_active == True)
        )
        active_overrides = {str(row.resort_id): row for row in ov_result.scalars().all()}

    override_updates: list[dict] = []
    for weather in weather_results:
        override = active_overrides.get(weather.resort_id)
        if not override:
            continue
        new_cumulative = float(override.cumulative_new_snow_since_cm or 0) + (weather.new_snow_24h_cm or 0)
        threshold = float(override.new_snow_threshold_cm or 20)
        if new_cumulative >= threshold:
            # Significant new snow — expire the override, use live data
            override_updates.append({"id": override.id, "is_active": False, "cumulative": new_cumulative})
            slug = resort_meta_map.get(weather.resort_id, {}).get("slug", weather.resort_id)
            logger.info(
                "Manual override expired for %s: %.1fcm cumulative new snow >= %.1fcm threshold",
                slug, new_cumulative, threshold,
            )
        else:
            # Override still valid — use override depth
            weather.snow_depth_cm = float(override.override_depth_cm)
            weather.depth_source = "manual_override"
            override_updates.append({"id": override.id, "is_active": True, "cumulative": new_cumulative})
            slug = resort_meta_map.get(weather.resort_id, {}).get("slug", weather.resort_id)
            logger.info(
                "Applied manual override for %s: %.1fcm (%.1fcm/%.1fcm new snow accumulated)",
                slug, override.override_depth_cm, new_cumulative, threshold,
            )

    if override_updates:
        async with SessionLocal() as session:
            for u in override_updates:
                await session.execute(
                    _update(ResortDepthOverride)
                    .where(ResortDepthOverride.id == u["id"])
                    .values(cumulative_new_snow_since_cm=u["cumulative"], is_active=u["is_active"])
                )
            await session.commit()

    # Run data quality validation for each resort
    for weather in weather_results:
        resort = resort_meta_map.get(weather.resort_id, {})
        weather.previous_depth_cm = previous_depths.get(weather.resort_id)
        quality, flags = run_validation(
            resort=resort,
            depth_cm=weather.snow_depth_cm,
            openmeteo_depth_cm=weather.openmeteo_depth_cm,
            previous_depth_cm=weather.previous_depth_cm,
            snowfall_24h_cm=weather.new_snow_24h_cm,
            avg_temp_c=weather.avg_temp_72h_c,
            depth_source=weather.depth_source,
            fetch_date=today,
        )
        weather.data_quality = quality.value
        weather.quality_flags = flags

    failure_rate = len(failed_ids) / len(resorts)
    if failure_rate > 0.05:
        logger.error(
            "Pipeline failure rate %.1f%% exceeds 5%% threshold (%d/%d failed)",
            failure_rate * 100, len(failed_ids), len(resorts),
        )
        # TODO: send SendGrid alert

    async with SessionLocal() as session:
        written, write_failures = await write_weather_snapshots(session, weather_results, today)
        logger.info("Wrote %d snapshots, %d failures", written, write_failures)

    # Score each resort at each horizon
    scored_at = datetime.now(timezone.utc)
    current_month = today.month

    async with SessionLocal() as session:
        for weather in weather_results:
            resort_meta = resort_meta_map.get(weather.resort_id, {})
            meta = ResortMeta(
                elevation_summit_m=resort_meta.get("elevation_summit_m"),
                aspect=resort_meta.get("aspect"),
                season_start_month=resort_meta.get("season_start_month"),
                season_end_month=resort_meta.get("season_end_month"),
            )
            current = CurrentConditions(
                snow_depth_cm=weather.snow_depth_cm,
                new_snow_72h_cm=weather.new_snow_72h_cm,
                temperature_c=weather.temperature_c,
                wind_speed_kmh=weather.wind_speed_kmh,
            )
            forecast_days = [
                ScorerForecastDay(
                    distance_days=(fc.forecast_date - today).days,
                    snowfall_cm=fc.snowfall_cm,
                    temperature_c=(
                        ((fc.temperature_max_c or 0) + (fc.temperature_min_c or 0)) / 2
                        if fc.temperature_max_c is not None and fc.temperature_min_c is not None
                        else None
                    ),
                    wind_speed_kmh=fc.wind_speed_max_kmh,
                    confidence=fc.confidence_score,
                )
                for fc in weather.forecasts
            ]

            scores_by_horizon = {}
            for horizon in SCORE_HORIZONS:
                scores_by_horizon[horizon] = compute_score(
                    current=current,
                    forecast_days=forecast_days,
                    meta=meta,
                    horizon_days=horizon,
                    current_month=current_month,
                )

            try:
                await write_scores(session, weather.resort_id, scores_by_horizon, scored_at)
            except Exception as exc:
                logger.error("Failed to write scores for %s: %s", weather.resort_id, exc)

    # Update global ranks for each horizon
    async with SessionLocal() as session:
        for horizon in SCORE_HORIZONS:
            await update_global_ranks(session, horizon, scored_at)

    logger.info("Pipeline completed successfully at %s", datetime.now(timezone.utc).isoformat())


def start_scheduler() -> None:
    scheduler = AsyncIOScheduler()
    # Parse cron expression: "0 6 * * *" → minute=0, hour=6
    cron_parts = PIPELINE_CRON_SCHEDULE.split()
    trigger = CronTrigger(
        minute=cron_parts[0],
        hour=cron_parts[1],
        day=cron_parts[2],
        month=cron_parts[3],
        day_of_week=cron_parts[4],
        timezone="UTC",
    )
    scheduler.add_job(run_pipeline, trigger, id="daily_pipeline", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started. Next run: %s", scheduler.get_job("daily_pipeline").next_run_time)

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_scheduler()
