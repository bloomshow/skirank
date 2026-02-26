"""
Async HTTP fetcher for Open-Meteo weather API + NWS snowfall forecasts.

Groups resorts into batches of PIPELINE_BATCH_SIZE and makes concurrent requests
to the Open-Meteo /v1/forecast endpoint for both current conditions and 16-day forecasts.

For US resorts, NWS gridpoint forecasts (HRRR, 3km resolution) are fetched and
overlaid onto the Open-Meteo snowfall values, which are more accurate for complex
mountain terrain than Open-Meteo's global ensemble model.
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

# NWS API settings
NWS_POINTS_BASE = "https://api.weather.gov/points"
NWS_USER_AGENT = "SkiRank/1.0 (skirank.app)"
NWS_TIMEOUT = 20.0       # NWS can be slow
NWS_MAX_CONCURRENT = 8   # Limit concurrent NWS connections


@dataclass
class ResortWeatherData:
    resort_id: str
    fetched_at: datetime
    # Current conditions (today)
    snow_depth_cm: float | None = None
    new_snow_24h_cm: float | None = None
    new_snow_72h_cm: float | None = None
    temperature_c: float | None = None
    avg_temp_72h_c: float | None = None   # 72h average temperature (for validation)
    wind_speed_kmh: float | None = None
    weather_code: int | None = None
    depth_source: str = "open_meteo"
    openmeteo_depth_cm: float | None = None  # Open-Meteo depth before any station override
    # Data quality (set by validator in scheduler)
    data_quality: str = "good"
    quality_flags: list = field(default_factory=list)
    previous_depth_cm: float | None = None   # Most recent DB depth before this run
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
    source: str = "open_meteo"


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

        # 72h average temperature (for quality validation)
        temp_72h = [v for v in temp_series[-72:] if v is not None]
        avg_temp_72h_c = round(sum(temp_72h) / len(temp_72h), 1) if temp_72h else None

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
                openmeteo_depth_cm=snow_depth_cm,  # preserved before any station override
                new_snow_24h_cm=round(new_24h / 10, 1) if new_24h else 0.0,  # mm → cm
                new_snow_72h_cm=round(new_72h / 10, 1) if new_72h else 0.0,
                temperature_c=temperature_c,
                avg_temp_72h_c=avg_temp_72h_c,
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


# ---------------------------------------------------------------------------
# NWS snowfall overlay (US resorts only)
# ---------------------------------------------------------------------------

async def _fetch_nws_daily_snowfall(
    client: httpx.AsyncClient,
    resort: dict,
    semaphore: asyncio.Semaphore,
) -> dict[date, float] | None:
    """
    Fetch NWS gridpoint forecast for a single US resort.

    Two-step: /points/{lat},{lon} → grid URL → snowfallAmount time series.
    Returns {date: snowfall_cm} for all dates in the NWS forecast, or None on
    any failure so the caller can fall back to Open-Meteo values.
    """
    lat = resort["latitude"]
    lon = resort["longitude"]
    resort_id = resort["id"]

    async with semaphore:
        # Step 1: resolve WFO grid coordinates
        try:
            resp = await client.get(
                f"{NWS_POINTS_BASE}/{lat:.4f},{lon:.4f}",
                timeout=NWS_TIMEOUT,
            )
            resp.raise_for_status()
            grid_url = resp.json()["properties"]["forecastGridData"]
        except Exception as exc:
            logger.warning("NWS points lookup failed for %s (%.4f, %.4f): %s", resort_id, lat, lon, exc)
            return None

        # Step 2: fetch gridpoint forecast data
        try:
            resp = await client.get(grid_url, timeout=NWS_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("NWS grid data failed for %s: %s", resort_id, exc)
            return None

    # Parse snowfallAmount — NWS returns SI units (wmoUnit:mm) even for US forecasts.
    # validTime format: "2026-02-26T06:00:00+00:00/PT6H"
    # value: total snowfall in the stated unit during that interval
    try:
        snowfall_props = data["properties"].get("snowfallAmount", {})
        uom = snowfall_props.get("uom", "")
        values = snowfall_props.get("values", [])
        if not values:
            logger.debug("NWS returned no snowfallAmount values for %s", resort_id)
            return None

        daily_raw: dict[date, float] = {}
        for entry in values:
            raw_val = entry.get("value")
            if raw_val is None:
                continue
            time_str = entry.get("validTime", "").split("/")[0]
            try:
                dt = datetime.fromisoformat(time_str).astimezone(timezone.utc)
            except ValueError:
                continue
            day = dt.date()
            daily_raw[day] = daily_raw.get(day, 0.0) + float(raw_val)

        if not daily_raw:
            return None

        # Convert to cm based on the unit returned by NWS
        def _to_cm(v: float) -> float:
            if "mm" in uom:
                return round(v / 10, 1)    # mm → cm
            elif "in" in uom:
                return round(v * 2.54, 1)  # inches → cm
            return round(v, 1)             # assume cm already

        return {d: _to_cm(v) for d, v in daily_raw.items()}

    except (KeyError, TypeError) as exc:
        logger.warning("NWS parse error for %s: %s", resort_id, exc)
        return None


async def fetch_nws_snowfall_overlays(
    us_resorts: list[dict],
) -> dict[str, dict[date, float]]:
    """
    Concurrently fetch NWS snowfall forecasts for all US resorts.

    Returns resort_id → {date: snowfall_cm}. Resorts that fail are excluded
    (caller falls back to Open-Meteo for them).
    """
    if not us_resorts:
        return {}

    semaphore = asyncio.Semaphore(NWS_MAX_CONCURRENT)
    nws_headers = {"User-Agent": NWS_USER_AGENT, "Accept": "application/geo+json"}

    async with httpx.AsyncClient(headers=nws_headers) as client:
        tasks = [
            _fetch_nws_daily_snowfall(client, resort, semaphore)
            for resort in us_resorts
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    overlays: dict[str, dict[date, float]] = {}
    for resort, result in zip(us_resorts, raw_results):
        if isinstance(result, Exception):
            logger.warning("NWS task exception for %s: %s", resort["id"], result)
        elif result is not None:
            overlays[resort["id"]] = result

    logger.info(
        "NWS snowfall overlay: %d/%d US resorts succeeded",
        len(overlays), len(us_resorts),
    )
    return overlays


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

    For US resorts, NWS gridpoint snowfall forecasts are fetched and overlaid
    on top of Open-Meteo forecast snowfall values after the main batch fetch.

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

    # --- NWS snowfall overlay for US resorts ---
    us_resorts = [
        r for r in resorts
        if r.get("country") == "US" and r["id"] in successful_ids
    ]
    if us_resorts:
        logger.info(
            "Fetching NWS snowfall overlays for %d US resorts...", len(us_resorts)
        )
        try:
            nws_overlays = await fetch_nws_snowfall_overlays(us_resorts)
        except Exception as exc:
            logger.warning(
                "NWS overlay fetch failed entirely: %s — keeping Open-Meteo forecasts", exc
            )
            nws_overlays = {}

        if nws_overlays:
            result_map = {w.resort_id: w for w in results}
            applied = 0
            for resort_id, daily_snow in nws_overlays.items():
                weather = result_map.get(resort_id)
                if not weather:
                    continue
                for fc in weather.forecasts:
                    if fc.forecast_date in daily_snow:
                        fc.snowfall_cm = daily_snow[fc.forecast_date]
                        fc.source = "nws_hrrr"
                applied += 1
            logger.info(
                "Applied NWS snowfall to %d/%d US resorts",
                applied, len(us_resorts),
            )

    return results, failed_ids
