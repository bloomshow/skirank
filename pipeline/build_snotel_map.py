"""
One-time script to build the resort → Snotel station mapping.

Run from repo root:
    python -m pipeline.build_snotel_map

Fetches all active SNTL stations for relevant US states, then matches each
US resort to its best nearby station using a distance + elevation score.
Saves the result to data/resort_snotel_map.json.
"""
from __future__ import annotations

import asyncio
import csv
import json
import math
from pathlib import Path

import httpx

from pipeline.config import SNOTEL_API_URL, HTTP_TIMEOUT

US_STATES = ["WY", "CO", "UT", "CA", "MT", "ID", "NM", "OR", "WA", "VT", "ME", "NH"]

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_FILES = [
    DATA_DIR / "na_top50_resorts.csv",
    DATA_DIR / "resorts_seed.csv",
]
OUTPUT_FILE = DATA_DIR / "resort_snotel_map.json"

MAX_DISTANCE_KM = 60.0
MAX_ELEV_DIFF_M = 700.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_us_resorts() -> list[dict]:
    seen_slugs: set[str] = set()
    resorts: list[dict] = []
    for csv_file in CSV_FILES:
        if not csv_file.exists():
            continue
        with open(csv_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("country") != "US":
                    continue
                slug = row["slug"]
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                try:
                    resorts.append(
                        {
                            "slug": slug,
                            "name": row["name"],
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


async def fetch_stations_for_state(
    client: httpx.AsyncClient, state: str
) -> list[dict]:
    url = f"{SNOTEL_API_URL}/stations"
    params = {
        "networkCds": "SNTL",
        "stateCds": state,
        "activeOnly": "true",
    }
    try:
        response = await client.get(url, params=params, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        print(f"  Warning: failed to fetch stations for {state}: {exc}")
        return []


async def fetch_all_stations() -> list[dict]:
    async with httpx.AsyncClient() as client:
        tasks = [fetch_stations_for_state(client, state) for state in US_STATES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    stations: list[dict] = []
    for state, result in zip(US_STATES, results):
        if isinstance(result, Exception):
            print(f"  Warning: exception fetching stations for {state}: {result}")
            continue
        stations.extend(result)
    return stations


def build_mapping(resorts: list[dict], stations: list[dict]) -> dict:
    mapping: dict[str, dict] = {}

    for resort in resorts:
        slug = resort["slug"]
        resort_lat = resort["latitude"]
        resort_lon = resort["longitude"]
        resort_elev_m = resort["elevation_summit_m"] or 0

        best_station: dict | None = None
        best_score = float("inf")
        best_dist_km = 0.0
        best_elev_m = 0.0

        for station in stations:
            try:
                station_lat = float(station["latitude"])
                station_lon = float(station["longitude"])
                # elevation is in feet — convert to metres
                station_elev_m = float(station.get("elevation", 0)) * 0.3048
            except (TypeError, ValueError):
                continue

            dist_km = haversine_km(resort_lat, resort_lon, station_lat, station_lon)
            if dist_km > MAX_DISTANCE_KM:
                continue

            elev_diff_m = abs(resort_elev_m - station_elev_m)
            if elev_diff_m > MAX_ELEV_DIFF_M:
                continue

            score = dist_km + elev_diff_m * 0.02
            if score < best_score:
                best_score = score
                best_station = station
                best_dist_km = dist_km
                best_elev_m = station_elev_m

        if best_station:
            triplet = best_station.get("stationTriplet", "")
            mapping[slug] = {
                "triplet": triplet,
                "name": best_station.get("name", ""),
                "distance_km": round(best_dist_km, 2),
                "station_elev_m": round(best_elev_m),
            }
            print(
                f"  {slug}: {best_station.get('name')} ({triplet})"
                f" dist={best_dist_km:.1f}km elev={best_elev_m:.0f}m"
            )
        else:
            print(
                f"  {slug}: no station within {MAX_DISTANCE_KM:.0f}km"
                f" / {MAX_ELEV_DIFF_M:.0f}m elev"
            )

    return mapping


async def main() -> None:
    print("Loading US resorts from CSVs...")
    resorts = load_us_resorts()
    print(f"  Found {len(resorts)} US resorts")

    print(f"Fetching Snotel stations for {len(US_STATES)} states: {', '.join(US_STATES)}")
    stations = await fetch_all_stations()
    print(f"  Found {len(stations)} SNTL stations total")

    print("Building resort → station mapping...")
    mapping = build_mapping(resorts, stations)
    print(f"  Mapped {len(mapping)}/{len(resorts)} resorts to Snotel stations")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"\nSaved mapping to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
