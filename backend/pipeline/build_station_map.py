"""
One-time script to build the global resort → snow-depth station mapping.

Uses the Synoptic Data API (synopticdata.com) which aggregates 100k+ stations
from SNOTEL, SCAN, Environment Canada, SYNOP, JMA, and many other networks —
covering US, Canada, Europe, Japan, and beyond through a single API.

Run from repo root:
    python -m pipeline.build_station_map

Requires SYNOPTIC_API_TOKEN in .env (free registration at synopticdata.com).
Saves data/resort_station_map.json.
"""
from __future__ import annotations

import asyncio
import csv
import json
import math
from pathlib import Path

import httpx

from pipeline.config import SYNOPTIC_API_URL, SYNOPTIC_API_TOKEN, HTTP_TIMEOUT

# Search radius sent to Synoptic (miles). ~64 km.
SEARCH_RADIUS_MILES = 40

# Client-side acceptance thresholds applied after candidate fetch.
MAX_DISTANCE_KM = 60.0
MAX_ELEV_DIFF_M = 700.0

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_FILES = [
    DATA_DIR / "na_top50_resorts.csv",
    DATA_DIR / "resorts_seed.csv",
]
OUTPUT_FILE = DATA_DIR / "resort_station_map.json"

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_all_resorts() -> list[dict]:
    """Load every resort from all CSVs, deduplicating by slug."""
    seen: set[str] = set()
    resorts: list[dict] = []
    for csv_file in CSV_FILES:
        if not csv_file.exists():
            continue
        with open(csv_file, newline="") as f:
            for row in csv.DictReader(f):
                slug = row["slug"]
                if slug in seen:
                    continue
                seen.add(slug)
                try:
                    resorts.append(
                        {
                            "slug": slug,
                            "name": row["name"],
                            "country": row.get("country", ""),
                            "latitude": float(row["latitude"]),
                            "longitude": float(row["longitude"]),
                            "elevation_summit_m": int(row["elevation_summit_m"])
                            if row.get("elevation_summit_m")
                            else None,
                        }
                    )
                except (ValueError, KeyError):
                    continue
    return resorts


async def fetch_nearby_stations(
    client: httpx.AsyncClient, resort: dict, sem: asyncio.Semaphore
) -> tuple[dict, list[dict]]:
    """Return (resort, candidate_stations) from Synoptic metadata endpoint."""
    async with sem:
        params = {
            "token": SYNOPTIC_API_TOKEN,
            "radius": f"{resort['latitude']},{resort['longitude']},{SEARCH_RADIUS_MILES}",
            "vars": "snow_depth",
            "status": "active",
            "output": "json",
        }
        try:
            resp = await client.get(
                f"{SYNOPTIC_API_URL}/stations/metadata",
                params=params,
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"  Warning: API error for {resort['slug']}: {exc}")
            return resort, []

        summary = data.get("SUMMARY", {})
        if summary.get("RESPONSE_CODE") != 1:
            # Code 2 = zero results, negative = API error
            return resort, []

        return resort, data.get("STATION", [])


def pick_best_station(resort: dict, candidates: list[dict]) -> dict | None:
    """Score candidates and return the best one within thresholds, or None."""
    resort_elev_m = resort["elevation_summit_m"] or 0
    best: dict | None = None
    best_score = float("inf")
    best_dist_km = 0.0
    best_elev_m = 0.0

    for station in candidates:
        try:
            station_lat = float(station["LATITUDE"])
            station_lon = float(station["LONGITUDE"])
            # Synoptic elevation is in feet by default
            station_elev_m = float(station.get("ELEVATION", 0)) * 0.3048
        except (TypeError, ValueError):
            continue

        dist_km = haversine_km(
            resort["latitude"], resort["longitude"], station_lat, station_lon
        )
        if dist_km > MAX_DISTANCE_KM:
            continue

        elev_diff_m = abs(resort_elev_m - station_elev_m)
        if elev_diff_m > MAX_ELEV_DIFF_M:
            continue

        score = dist_km + elev_diff_m * 0.02
        if score < best_score:
            best_score = score
            best = station
            best_dist_km = dist_km
            best_elev_m = station_elev_m

    if best is None:
        return None

    return {
        "stid": best["STID"],
        "name": best.get("NAME", ""),
        "network": best.get("MNET_SHORTNAME", best.get("MNET_ID", "")),
        "distance_km": round(best_dist_km, 2),
        "station_elev_m": round(best_elev_m),
    }


async def main() -> None:
    if not SYNOPTIC_API_TOKEN:
        print("ERROR: SYNOPTIC_API_TOKEN is not set. Add it to .env and retry.")
        return

    print("Loading resorts from CSVs...")
    resorts = load_all_resorts()
    print(f"  Found {len(resorts)} resorts across all regions")

    print(
        f"Querying Synoptic for stations within {SEARCH_RADIUS_MILES} miles of each resort..."
    )
    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient() as client:
        tasks = [fetch_nearby_stations(client, r, sem) for r in resorts]
        results = await asyncio.gather(*tasks)

    print("Scoring and selecting best station per resort...")
    mapping: dict[str, dict] = {}
    matched = 0
    for resort, candidates in results:
        slug = resort["slug"]
        best = pick_best_station(resort, candidates)
        if best:
            mapping[slug] = best
            matched += 1
            print(
                f"  {slug}: {best['name']} ({best['stid']})"
                f" dist={best['distance_km']:.1f}km elev={best['station_elev_m']}m"
            )
        else:
            print(
                f"  {slug}: no station within {MAX_DISTANCE_KM:.0f}km"
                f" / {MAX_ELEV_DIFF_M:.0f}m — will use Open-Meteo"
            )

    print(f"\nMapped {matched}/{len(resorts)} resorts to snow-depth stations")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
