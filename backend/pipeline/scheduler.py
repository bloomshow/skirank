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

    # Build a lookup for resort metadata (used for Snotel override and scoring below)
    resort_meta_map = {r["id"]: r for r in resorts}

    # Enrich snow depth from on-mountain stations for all resorts (overrides Open-Meteo grid estimate)
    from pipeline.station_fetcher import fetch_station_depths
    all_slugs = [r["slug"] for r in resorts]
    station_readings = await fetch_station_depths(all_slugs)

    for weather in weather_results:
        resort = resort_meta_map.get(weather.resort_id, {})
        slug = resort.get("slug")
        if slug and slug in station_readings:
            weather.snow_depth_cm = station_readings[slug].snow_depth_cm
            logger.info(
                "Station override for %s: %.1f cm (stid=%s, date=%s)",
                slug,
                weather.snow_depth_cm,
                station_readings[slug].stid,
                station_readings[slug].data_date,
            )

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
