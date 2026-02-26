"""
Fetches snow depth data from the USDA NRCS Snotel network for US resorts.

Loads data/resort_snotel_map.json (built by build_snotel_map.py) and queries
the AWDB REST API for the most recent daily snow depth reading at each mapped
station.  Resorts without a mapping are silently skipped; callers fall back to
Open-Meteo for those.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import date, timedelta  # timedelta used in fetch_snotel_depths
from pathlib import Path
from typing import Any

import httpx

from pipeline.config import SNOTEL_API_URL, HTTP_TIMEOUT, HTTP_RETRIES, HTTP_BACKOFF_FACTOR

logger = logging.getLogger(__name__)

MAP_FILE = Path(__file__).parent.parent / "data" / "resort_snotel_map.json"


@dataclass
class SnotelReading:
    resort_slug: str
    snow_depth_cm: float
    station_triplet: str
    data_date: str


def _load_snotel_map() -> dict[str, dict]:
    if not MAP_FILE.exists():
        logger.warning(
            "Snotel map not found at %s — run pipeline.build_snotel_map first", MAP_FILE
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
                "Snotel fetch attempt %d/%d failed: %s — retrying in %.1fs",
                attempt + 1,
                HTTP_RETRIES,
                exc,
                wait,
            )
            await asyncio.sleep(wait)
    raise RuntimeError(f"All {HTTP_RETRIES} Snotel fetch attempts failed") from last_exc


def _parse_snotel_response(
    data: list | dict, triplet_to_slug: dict[str, str]
) -> dict[str, SnotelReading]:
    """
    Parse AWDB /data response into SnotelReading objects.

    The AWDB REST API returns a list of station objects, each with a ``data``
    list of element records.  Each element record contains a ``values`` list
    (one entry per day from beginDate to endDate) and a ``beginDate`` string.
    Snow depth values are in inches; we convert to cm here.
    """
    results: dict[str, SnotelReading] = {}
    items = data if isinstance(data, list) else [data]

    for item in items:
        triplet = item.get("stationTriplet", "")
        slug = triplet_to_slug.get(triplet)
        if not slug:
            continue

        station_data_list = item.get("data", [])
        if not station_data_list:
            logger.debug("No data entries for Snotel station %s", triplet)
            continue

        # There is typically one element record (SNWD); take the first.
        element_data = station_data_list[0]
        values: list = element_data.get("values", [])

        # values is a list of {date, value} dicts — walk backwards for most recent non-null.
        snow_depth_in: float | None = None
        data_date: str = ""
        for entry in reversed(values):
            val = entry.get("value")
            if val is not None:
                try:
                    snow_depth_in = float(val)
                    data_date = entry.get("date", "")
                    break
                except (ValueError, TypeError):
                    continue

        if snow_depth_in is not None:
            snow_depth_cm = round(snow_depth_in * 2.54, 1)
            results[slug] = SnotelReading(
                resort_slug=slug,
                snow_depth_cm=snow_depth_cm,
                station_triplet=triplet,
                data_date=data_date,
            )
            logger.debug(
                "Snotel %s (%s): %.1f in → %.1f cm on %s",
                slug,
                triplet,
                snow_depth_in,
                snow_depth_cm,
                data_date,
            )

    return results


async def fetch_snotel_depths(slugs: list[str]) -> dict[str, SnotelReading]:
    """
    Fetch Snotel snow depth for the given resort slugs.

    Batches all mapped stations into a single API call, queries the last 3 days,
    and returns the most recent non-null reading per resort.

    Returns {resort_slug: SnotelReading} for resorts with Snotel data.
    Slugs with no mapping or no data are omitted; callers should fall back to
    Open-Meteo for those.
    """
    snotel_map = _load_snotel_map()
    if not snotel_map:
        return {}

    # Filter to slugs that have a station mapping.
    mapped = {slug: snotel_map[slug] for slug in slugs if slug in snotel_map}
    if not mapped:
        return {}

    triplet_to_slug = {info["triplet"]: slug for slug, info in mapped.items()}
    triplets = list(triplet_to_slug.keys())

    today = date.today()
    begin_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    url = f"{SNOTEL_API_URL}/data"
    params = {
        "stationTriplets": ",".join(triplets),
        "elements": "SNWD",
        "beginDate": begin_date,
        "endDate": end_date,
    }

    logger.info(
        "Fetching Snotel SNWD for %d stations (%s to %s)",
        len(triplets),
        begin_date,
        end_date,
    )

    try:
        async with httpx.AsyncClient() as client:
            data = await _fetch_with_retry(client, url, params)
    except Exception as exc:
        logger.error("Snotel API fetch failed: %s", exc)
        return {}

    readings = _parse_snotel_response(data, triplet_to_slug)
    logger.info(
        "Snotel returned readings for %d/%d mapped resorts", len(readings), len(mapped)
    )
    return readings
