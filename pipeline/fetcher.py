"""
Async HTTP fetcher for Open-Meteo weather API.

Groups resorts into batches of PIPELINE_BATCH_SIZE and makes concurrent requests
to the Open-Meteo /v1/forecast endpoint for both current conditions and 16-day forecasts.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

import httpx

from pipeline.config import (
    OPEN_METEO_FORECAST_URL,
    PIPELINE_BATCH_SIZE,
    HTTP_RETRIES,
    HTTP_BACKOFF_FACTOR,
    HTTP_TIMEOUT,
)

logger = logging.getLogger(__name__)

# Open-Meteo variable names
HOURLY_VARS = ["snow_depth", "snowfall", "temperature_2m", "windspeed_10m", "weathercode"]
DAILY_VARS = [
    "snowfall_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "windspeed_10m_max",
    "precipitation_probability_max",
    "weathercode",
]


@dataclass
class ResortWeatherData:
    resort_id: str
    fetched_at: datetime
    # Current conditions (today)
    snow_depth_cm: float | None = None
    new_snow_24h_cm: float | None = None
    new_snow_72h_cm: float | None = None
    temperature_c: float | None = None
    wind_speed_kmh: float | None = None
    weather_code: int | None = None
    # 16-day forecasts
    forecasts: list[ForecastDay] = field(default_factory=list)


@dataclass
class ForecastDay:
    forecast_date: date
    snowfall_cm: float | None
    temperature_max_c: float | None
    temperature_min_c: float | None
    wind_speed_max_kmh: float | None
    precipitation_prob_pct: int | None
    weather_code: int | None
    confidence_score: float


async def _fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
) -> dict[str, Any]:
    """Fetch URL with exponential backoff retry."""
    last_exc: Exception | None = None
    for attempt in range(HTTP_RETRIES):
        try:
            response = await client.get(url, params=params, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            wait = HTTP_BACKOFF_FACTOR * (2 ** attempt)
            logger.warning(
                "Fetch attempt %d/%d failed: %s — retrying in %.1fs",
                attempt + 1, HTTP_RETRIES, exc, wait,
            )
            await asyncio.sleep(wait)
    raise RuntimeError(f"All {HTTP_RETRIES} fetch attempts failed") from last_exc


def _parse_batch_response(
    data: dict[str, Any],
    resort_ids: list[str],
    fetched_at: datetime,
) -> list[ResortWeatherData]:
    """
    Parse an Open-Meteo batch response into ResortWeatherData objects.

    Open-Meteo returns a list of results when multiple lat/lng are submitted.
    """
    # When batching, Open-Meteo returns a list; single resort returns a dict.
    items = data if isinstance(data, list) else [data]
    results = []

    for resort_id, item in zip(resort_ids, items):
        if "error" in item:
            logger.error("Open-Meteo error for resort %s: %s", resort_id, item.get("reason"))
            continue

        hourly = item.get("hourly", {})
        daily = item.get("daily", {})

        # Current snow depth (metres → cm), latest non-null value
        snow_depth_m_series = hourly.get("snow_depth", [])
        snow_depth_cm = None
        for v in reversed(snow_depth_m_series):
            if v is not None:
                snow_depth_cm = round(v * 100, 1)
                break

        # New snow: sum hourly snowfall (mm) over last 24h and 72h windows
        snowfall_mm_series = hourly.get("snowfall", [])
        new_24h = sum(v for v in snowfall_mm_series[-24:] if v is not None)
        new_72h = sum(v for v in snowfall_mm_series[-72:] if v is not None)

        # Current temperature at 2m (°C), latest non-null
        temp_series = hourly.get("temperature_2m", [])
        temperature_c = None
        for v in reversed(temp_series):
            if v is not None:
                temperature_c = v
                break

        # Current wind speed (km/h): max over the last 24 h of hourly data.
        # Using the max rather than the latest instantaneous reading gives a
        # more representative picture of resort conditions (gusts, ridge wind).
        # Fall back to today's daily windspeed_10m_max when hourly is absent.
        wind_series = hourly.get("windspeed_10m", [])
        recent_winds = [v for v in wind_series[-24:] if v is not None]
        if recent_winds:
            wind_speed_kmh = max(recent_winds)
        else:
            # Fall back to day-0 daily max
            wind_speed_kmh = _safe_float(daily.get("windspeed_10m_max", []), 0)

        # Weather code, latest non-null
        wcode_series = hourly.get("weathercode", [])
        weather_code = None
        for v in reversed(wcode_series):
            if v is not None:
                weather_code = int(v)
                break

        # Build daily forecasts
        daily_dates = daily.get("time", [])
        daily_snowfall = daily.get("snowfall_sum", [])
        daily_tmax = daily.get("temperature_2m_max", [])
        daily_tmin = daily.get("temperature_2m_min", [])
        daily_wind_max = daily.get("windspeed_10m_max", [])
        daily_precip_prob = daily.get("precipitation_probability_max", [])
        daily_wcode = daily.get("weathercode", [])

        forecasts = []
        for i, date_str in enumerate(daily_dates):
            dist_days = i  # distance from today
            # Confidence decays linearly: 1.0 at day 0, 0.5 at day 16
            confidence = round(max(0.1, 1.0 - (dist_days / 16) * 0.5), 3)
            forecasts.append(
                ForecastDay(
                    forecast_date=date.fromisoformat(date_str),
                    snowfall_cm=_safe_float(daily_snowfall, i),
                    temperature_max_c=_safe_float(daily_tmax, i),
                    temperature_min_c=_safe_float(daily_tmin, i),
                    wind_speed_max_kmh=_safe_float(daily_wind_max, i),
                    precipitation_prob_pct=_safe_int(daily_precip_prob, i),
                    weather_code=_safe_int(daily_wcode, i),
                    confidence_score=confidence,
                )
            )

        results.append(
            ResortWeatherData(
                resort_id=resort_id,
                fetched_at=fetched_at,
                snow_depth_cm=snow_depth_cm,
                new_snow_24h_cm=round(new_24h / 10, 1) if new_24h else 0.0,  # mm → cm
                new_snow_72h_cm=round(new_72h / 10, 1) if new_72h else 0.0,
                temperature_c=temperature_c,
                wind_speed_kmh=wind_speed_kmh,
                weather_code=weather_code,
                forecasts=forecasts,
            )
        )

    return results


def _safe_float(lst: list, i: int) -> float | None:
    try:
        v = lst[i]
        return float(v) if v is not None else None
    except (IndexError, TypeError):
        return None


def _safe_int(lst: list, i: int) -> int | None:
    try:
        v = lst[i]
        return int(v) if v is not None else None
    except (IndexError, TypeError):
        return None


async def fetch_batch(
    client: httpx.AsyncClient,
    resorts: list[dict],  # list of {id, latitude, longitude}
) -> list[ResortWeatherData]:
    """Fetch weather data for a batch of up to PIPELINE_BATCH_SIZE resorts."""
    if not resorts:
        return []

    lats = ",".join(str(r["latitude"]) for r in resorts)
    lngs = ",".join(str(r["longitude"]) for r in resorts)

    params = {
        "latitude": lats,
        "longitude": lngs,
        "hourly": ",".join(HOURLY_VARS),
        "daily": ",".join(DAILY_VARS),
        "forecast_days": 16,
        "timezone": "UTC",
        "timeformat": "iso8601",
    }

    # Pass summit elevation so Open-Meteo samples at mountain altitude, not valley floor
    if all(r.get("elevation_summit_m") for r in resorts):
        params["elevation"] = ",".join(str(r["elevation_summit_m"]) for r in resorts)

    fetched_at = datetime.now(timezone.utc)
    resort_ids = [r["id"] for r in resorts]

    try:
        data = await _fetch_with_retry(client, OPEN_METEO_FORECAST_URL, params)
    except RuntimeError as exc:
        logger.error("Batch fetch failed for %d resorts: %s", len(resorts), exc)
        return []

    return _parse_batch_response(data, resort_ids, fetched_at)


async def fetch_all_resorts(
    resorts: list[dict],
) -> tuple[list[ResortWeatherData], list[str]]:
    """
    Fetch weather data for all resorts, batched by PIPELINE_BATCH_SIZE.

    Returns (successful_results, failed_resort_ids).
    """
    results: list[ResortWeatherData] = []
    failed_ids: list[str] = []

    batches = [
        resorts[i : i + PIPELINE_BATCH_SIZE]
        for i in range(0, len(resorts), PIPELINE_BATCH_SIZE)
    ]

    async with httpx.AsyncClient() as client:
        tasks = [fetch_batch(client, batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_ids = set()
    for batch, batch_result in zip(batches, batch_results):
        if isinstance(batch_result, Exception):
            logger.error("Batch exception: %s", batch_result)
            failed_ids.extend(r["id"] for r in batch)
        else:
            results.extend(batch_result)
            successful_ids.update(r.resort_id for r in batch_result)

    # Any resort not in successful_ids from a non-exception batch also failed
    for batch, batch_result in zip(batches, batch_results):
        if not isinstance(batch_result, Exception):
            for resort in batch:
                if resort["id"] not in successful_ids:
                    failed_ids.append(resort["id"])

    return results, failed_ids
