"""
Fetches snow depth from the Synoptic Data API for all resorts that have a
mapped station in data/resort_station_map.json.

Synoptic aggregates SNOTEL, SCAN, Environment Canada, SYNOP, JMA, and 40+
other networks, giving global coverage through a single API.

Requires SYNOPTIC_API_TOKEN in .env.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

import httpx

from pipeline.config import (
    SYNOPTIC_API_URL,
    SYNOPTIC_API_TOKEN,
    HTTP_TIMEOUT,
    HTTP_RETRIES,
    HTTP_BACKOFF_FACTOR,
)

logger = logging.getLogger(__name__)

MAP_FILE = Path(__file__).parent.parent / "data" / "resort_station_map.json"

# Fetch last 3 days of data to handle station reporting lag (in minutes).
RECENT_MINUTES = 4320

# Max STIDs per API request — well within Synoptic free-tier limits.
BATCH_SIZE = 100


@dataclass
class StationReading:
    resort_slug: str
    snow_depth_cm: float
    stid: str
    data_date: str


def _load_station_map() -> dict[str, dict]:
    if not MAP_FILE.exists():
        logger.warning(
            "Station map not found at %s — run pipeline.build_station_map first", MAP_FILE
        )
        return {}
    with open(MAP_FILE) as f:
        return json.load(f)


async def _fetch_with_retry(
    client: httpx.AsyncClient, url: str, params: dict
) -> Any:
    last_exc: Exception | None = None
    for attempt in range(HTTP_RETRIES):
        try:
            response = await client.get(url, params=params, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            wait = HTTP_BACKOFF_FACTOR * (2**attempt)
            logger.warning(
                "Synoptic fetch attempt %d/%d failed: %s — retrying in %.1fs",
                attempt + 1,
                HTTP_RETRIES,
                exc,
                wait,
            )
            await asyncio.sleep(wait)
    raise RuntimeError(f"All {HTTP_RETRIES} Synoptic fetch attempts failed") from last_exc


def _snow_depth_to_cm(value: float, unit: str) -> float:
    """Convert a Synoptic snow_depth reading to centimetres."""
    unit_lower = unit.lower()
    if "millimeter" in unit_lower or unit_lower == "mm":
        return round(value / 10, 1)
    if "meter" in unit_lower:
        return round(value * 100, 1)
    if "inch" in unit_lower:
        return round(value * 2.54, 1)
    if "centimeter" in unit_lower or unit_lower == "cm":
        return round(value, 1)
    # Unknown unit — log and skip rather than silently produce garbage values.
    logger.warning("Unknown snow_depth unit '%s' for value %.1f — skipping", unit, value)
    return round(value / 10, 1)


def _parse_timeseries_response(
    data: dict,
    stid_to_slugs: dict[str, list[str]],
    snow_depth_unit: str,
) -> dict[str, StationReading]:
    """Parse a Synoptic timeseries response into StationReading objects."""
    results: dict[str, StationReading] = {}

    for station in data.get("STATION", []):
        stid = station.get("STID", "")
        slugs = stid_to_slugs.get(stid)
        if not slugs:
            continue

        obs = station.get("OBSERVATIONS", {})
        # Synoptic uses set suffixes: snow_depth_set_1, snow_depth_set_2, etc.
        # Pick the first available set.
        depth_key = next(
            (k for k in obs if k.startswith("snow_depth")), None
        )
        times_key = "date_time"

        if not depth_key or times_key not in obs:
            logger.debug("No snow_depth observations for station %s", stid)
            continue

        depths = obs[depth_key]
        times = obs[times_key]

        # Walk backwards to find the most recent non-null value.
        snow_depth_cm: float | None = None
        data_date = ""
        for i in range(len(depths) - 1, -1, -1):
            val = depths[i]
            if val is not None:
                try:
                    snow_depth_cm = _snow_depth_to_cm(float(val), snow_depth_unit)
                    # Synoptic timestamps are ISO-8601 UTC strings.
                    raw_ts = times[i] if i < len(times) else ""
                    data_date = raw_ts[:10] if raw_ts else ""
                    break
                except (ValueError, TypeError):
                    continue

        if snow_depth_cm is None:
            logger.debug("All snow_depth values null for station %s", stid)
            continue

        # Apply this reading to every resort that maps to this station.
        for slug in slugs:
            results[slug] = StationReading(
                resort_slug=slug,
                snow_depth_cm=snow_depth_cm,
                stid=stid,
                data_date=data_date,
            )

    return results


async def _fetch_batch(
    client: httpx.AsyncClient,
    stids: list[str],
    stid_to_slugs: dict[str, list[str]],
) -> dict[str, StationReading]:
    """Fetch one batch of STIDs from Synoptic timeseries endpoint."""
    params = {
        "token": SYNOPTIC_API_TOKEN,
        "stid": ",".join(stids),
        "recent": str(RECENT_MINUTES),
        "vars": "snow_depth",
        "units": "metric",
        "output": "json",
    }

    try:
        data = await _fetch_with_retry(
            client, f"{SYNOPTIC_API_URL}/stations/timeseries", params
        )
    except Exception as exc:
        logger.error("Synoptic timeseries batch failed: %s", exc)
        return {}

    # Determine the unit Synoptic used (should be "Meters" with units=metric).
    snow_depth_unit = (
        data.get("UNITS", {}).get("snow_depth", "Meters")
    )

    return _parse_timeseries_response(data, stid_to_slugs, snow_depth_unit)


async def fetch_station_depths(slugs: list[str]) -> dict[str, StationReading]:
    """
    Fetch snow depth for the given resort slugs via Synoptic Data API.

    Loads data/resort_station_map.json, batches all mapped STIDs into
    API requests, and returns the most recent non-null reading per resort.

    Slugs with no mapping or no recent data are omitted; callers should
    fall back to Open-Meteo for those.
    """
    if not SYNOPTIC_API_TOKEN:
        logger.warning(
            "SYNOPTIC_API_TOKEN not set — skipping station snow-depth fetch"
        )
        return {}

    station_map = _load_station_map()
    if not station_map:
        return {}

    # Filter to slugs that have a mapping.
    mapped = {slug: station_map[slug] for slug in slugs if slug in station_map}
    if not mapped:
        return {}

    # Build STID → list[slug] so multiple resorts sharing a station all get the reading.
    stid_to_slugs: dict[str, list[str]] = {}
    for slug, info in mapped.items():
        stid = info["stid"]
        stid_to_slugs.setdefault(stid, []).append(slug)

    unique_stids = list(stid_to_slugs.keys())
    batches = [
        unique_stids[i : i + BATCH_SIZE] for i in range(0, len(unique_stids), BATCH_SIZE)
    ]

    logger.info(
        "Fetching Synoptic snow_depth for %d stations (%d batches, last %d min)",
        len(unique_stids),
        len(batches),
        RECENT_MINUTES,
    )

    results: dict[str, StationReading] = {}
    async with httpx.AsyncClient() as client:
        tasks = [_fetch_batch(client, batch, stid_to_slugs) for batch in batches]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for batch_result in batch_results:
        if isinstance(batch_result, Exception):
            logger.error("Synoptic batch exception: %s", batch_result)
        else:
            results.update(batch_result)

    logger.info(
        "Synoptic returned readings for %d/%d mapped resorts",
        len(results),
        len(mapped),
    )
    return results
