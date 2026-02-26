from __future__ import annotations

import asyncio
import csv
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from sqlalchemy import select, update, func, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.db import init_db, AsyncSessionLocal
from backend.models.resort import Resort

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_KEY = "skirank-admin-2026"
DATA_CSV = Path(__file__).parent.parent.parent / "data" / "resorts_200.csv"

# ---------------------------------------------------------------------------
# Hierarchy mapping tables
# ---------------------------------------------------------------------------
CONTINENT_MAP = {
    "US": "North America", "CA": "North America",
    "FR": "Europe", "AT": "Europe", "CH": "Europe", "IT": "Europe",
    "DE": "Europe", "NO": "Europe", "SE": "Europe", "FI": "Europe",
    "ES": "Europe", "AD": "Europe", "SK": "Europe", "SI": "Europe",
    "BG": "Europe", "RO": "Europe", "GB": "Europe",
    "JP": "Asia", "KR": "Asia",
    "AR": "South America", "CL": "South America",
    "AU": "Oceania", "NZ": "Oceania",
}

US_SKI_REGION_MAP = {
    "Colorado": "Colorado", "Utah": "Utah",
    "California": "California", "Nevada": "California",
    "Washington": "Pacific Northwest", "Oregon": "Pacific Northwest",
    "Montana": "Mountain West", "Wyoming": "Mountain West", "Idaho": "Mountain West",
    "Vermont": "Northeast USA", "New Hampshire": "Northeast USA",
    "New York": "Northeast USA", "Maine": "Northeast USA",
}

CA_SKI_REGION_MAP = {
    "British Columbia": "British Columbia", "Alberta": "Alberta",
    "Quebec": "Eastern Canada", "Ontario": "Eastern Canada",
    "Newfoundland": "Eastern Canada",
}

COUNTRY_SKI_REGION_MAP = {
    "FR": "French Alps", "CH": "Swiss Alps", "AT": "Austrian Alps",
    "IT": "Italian Alps", "NO": "Scandinavia", "SE": "Scandinavia",
    "FI": "Scandinavia", "ES": "Pyrenees & Iberia", "AD": "Pyrenees & Iberia",
}

AR_REGION_MAP = {"Andes": "Andes"}
CL_REGION_MAP = {"Andes": "Andes"}
AU_SKI_REGION = "Australian Alps"
NZ_SKI_REGION = "Southern Alps"

# Japan: Hokkaido → Hokkaido, others → Honshu
JP_REGION_MAP = {"Hokkaido": "Hokkaido"}

COUNTRY_LABEL_MAP = {
    "US": "United States", "CA": "Canada", "FR": "France", "AT": "Austria",
    "CH": "Switzerland", "IT": "Italy", "DE": "Germany", "NO": "Norway",
    "SE": "Sweden", "FI": "Finland", "ES": "Spain", "AD": "Andorra",
    "SK": "Slovakia", "SI": "Slovenia", "BG": "Bulgaria", "RO": "Romania",
    "GB": "Great Britain", "JP": "Japan", "KR": "South Korea",
    "AR": "Argentina", "CL": "Chile", "AU": "Australia", "NZ": "New Zealand",
}


def _compute_ski_region(country: str | None, region: str | None, subregion: str | None = None) -> str | None:
    if not country:
        return None
    if country == "US":
        # subregion holds the state name (e.g. "Colorado", "Utah")
        return US_SKI_REGION_MAP.get(subregion) if subregion else None
    if country == "CA":
        # subregion holds the province name (e.g. "British Columbia", "Alberta")
        return CA_SKI_REGION_MAP.get(subregion) if subregion else None
    if country == "JP":
        # region holds the prefecture (e.g. "Hokkaido", "Nagano", "Niigata")
        if region == "Hokkaido":
            return "Hokkaido"
        return "Honshu"  # all other JP prefectures
    if country in ("AR", "CL"):
        return "Andes"
    if country == "AU":
        return AU_SKI_REGION
    if country == "NZ":
        return NZ_SKI_REGION
    return COUNTRY_SKI_REGION_MAP.get(country)


def _require_key(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/migrate")
async def run_migrate(x_admin_key: str = Header(...)):
    _require_key(x_admin_key)
    await init_db()

    # Apply any missing columns via ALTER TABLE (idempotent via IF NOT EXISTS)
    alter_stmts = [
        "ALTER TABLE forecast_snapshots ADD COLUMN IF NOT EXISTS source VARCHAR(50)",
        "ALTER TABLE resorts ADD COLUMN IF NOT EXISTS continent VARCHAR(50)",
        "ALTER TABLE resorts ADD COLUMN IF NOT EXISTS ski_region VARCHAR(100)",
        # v1.5 data quality columns
        "ALTER TABLE weather_snapshots ADD COLUMN IF NOT EXISTS data_quality VARCHAR(20) DEFAULT 'good'",
        "ALTER TABLE weather_snapshots ADD COLUMN IF NOT EXISTS quality_flags JSONB DEFAULT '[]'",
        "ALTER TABLE weather_snapshots ADD COLUMN IF NOT EXISTS previous_depth_cm DECIMAL(6,1)",
    ]
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        for stmt in alter_stmts:
            await db.execute(text(stmt))
        await db.commit()

    return {"status": "ok", "message": "Tables created and columns migrated successfully"}


@router.post("/seed")
async def run_seed(x_admin_key: str = Header(...)):
    _require_key(x_admin_key)

    if not DATA_CSV.exists():
        raise HTTPException(status_code=500, detail=f"CSV not found at {DATA_CSV}")

    batch = []
    with open(DATA_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            batch.append({
                "id": uuid.uuid4(),
                "name": row["name"],
                "slug": row["slug"],
                "country": row.get("country") or None,
                "region": row.get("region") or None,
                "subregion": row.get("subregion") or None,
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "elevation_base_m": int(row["elevation_base_m"]) if row.get("elevation_base_m") else None,
                "elevation_summit_m": int(row["elevation_summit_m"]) if row.get("elevation_summit_m") else None,
                "aspect": row.get("aspect") or None,
                "vertical_drop_m": int(row["vertical_drop_m"]) if row.get("vertical_drop_m") else None,
                "num_runs": int(row["num_runs"]) if row.get("num_runs") else None,
                "season_start_month": int(row["season_start_month"]) if row.get("season_start_month") else None,
                "season_end_month": int(row["season_end_month"]) if row.get("season_end_month") else None,
                "timezone": row.get("timezone") or None,
                "website_url": row.get("website_url") or None,
            })

    if not batch:
        raise HTTPException(status_code=500, detail="CSV was empty")

    async with AsyncSessionLocal() as db:
        stmt = pg_insert(Resort).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["slug"],
            set_={
                "name": stmt.excluded.name,
                "country": stmt.excluded.country,
                "region": stmt.excluded.region,
                "subregion": stmt.excluded.subregion,
                "latitude": stmt.excluded.latitude,
                "longitude": stmt.excluded.longitude,
                "elevation_base_m": stmt.excluded.elevation_base_m,
                "elevation_summit_m": stmt.excluded.elevation_summit_m,
                "aspect": stmt.excluded.aspect,
                "vertical_drop_m": stmt.excluded.vertical_drop_m,
                "num_runs": stmt.excluded.num_runs,
                "season_start_month": stmt.excluded.season_start_month,
                "season_end_month": stmt.excluded.season_end_month,
                "timezone": stmt.excluded.timezone,
                "website_url": stmt.excluded.website_url,
            },
        )
        await db.execute(stmt)
        await db.commit()

    return {"status": "ok", "message": f"Upserted {len(batch)} resorts"}


@router.post("/run-pipeline")
async def trigger_pipeline(background_tasks: BackgroundTasks, x_admin_key: str = Header(...)):
    _require_key(x_admin_key)
    from pipeline.scheduler import run_pipeline
    background_tasks.add_task(run_pipeline)
    return {"status": "ok", "message": "Pipeline started in background — check Railway logs for progress"}


@router.post("/set-hierarchy")
async def set_hierarchy(x_admin_key: str = Header(...)):
    _require_key(x_admin_key)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Resort.id, Resort.country, Resort.region, Resort.subregion)
        )
        rows = result.all()

    updates = []
    for resort_id, country, region, subregion in rows:
        continent = CONTINENT_MAP.get(country) if country else None
        ski_region = _compute_ski_region(country, region, subregion)
        updates.append({"id": resort_id, "continent": continent, "ski_region": ski_region})

    async with AsyncSessionLocal() as db:
        for u in updates:
            await db.execute(
                update(Resort)
                .where(Resort.id == u["id"])
                .values(continent=u["continent"], ski_region=u["ski_region"])
            )
        await db.commit()

    assigned = sum(1 for u in updates if u["continent"] is not None)
    return {
        "status": "ok",
        "message": f"Set hierarchy for {assigned}/{len(updates)} resorts",
    }


@router.get("/quality-report")
async def quality_report(x_admin_key: str = Header(...)):
    """Data quality summary and list of flagged resorts."""
    _require_key(x_admin_key)

    from collections import Counter
    from backend.models.weather import WeatherSnapshot
    from backend.models.resort import Resort

    async with AsyncSessionLocal() as db:
        # Most recent snapshot per resort
        snap_subq = (
            select(WeatherSnapshot.resort_id, func.max(WeatherSnapshot.fetched_at).label("latest"))
            .group_by(WeatherSnapshot.resort_id)
            .subquery()
        )
        result = await db.execute(
            select(
                Resort.name,
                Resort.slug,
                WeatherSnapshot.data_quality,
                WeatherSnapshot.quality_flags,
                WeatherSnapshot.fetched_at,
            )
            .join(snap_subq, Resort.id == snap_subq.c.resort_id)
            .join(
                WeatherSnapshot,
                and_(
                    WeatherSnapshot.resort_id == Resort.id,
                    WeatherSnapshot.fetched_at == snap_subq.c.latest,
                ),
            )
            .order_by(Resort.name)
        )
        rows = result.all()

        last_run_result = await db.execute(select(func.max(WeatherSnapshot.fetched_at)))
        last_pipeline_run = last_run_result.scalar_one_or_none()

    quality_counts = Counter(row.data_quality or "good" for row in rows)
    flagged = [
        {
            "name": row.name,
            "slug": row.slug,
            "quality": row.data_quality or "good",
            "flags": row.quality_flags or [],
            "last_updated": row.fetched_at.isoformat() if row.fetched_at else None,
        }
        for row in rows
        if (row.data_quality or "good") in ("suspect", "unreliable", "stale")
    ]

    return {
        "quality_summary": dict(quality_counts),
        "total_resorts": len(rows),
        "flagged_resorts": sorted(flagged, key=lambda x: x["quality"]),
        "last_pipeline_run": last_pipeline_run.isoformat() if last_pipeline_run else None,
    }
