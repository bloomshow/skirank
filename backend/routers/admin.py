from __future__ import annotations

import csv
import uuid
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.db import init_db, AsyncSessionLocal
from backend.models.resort import Resort

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_KEY = "skirank-admin-2026"
DATA_CSV = Path(__file__).parent.parent.parent / "data" / "resorts_200.csv"


def _require_key(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/migrate")
async def run_migrate(x_admin_key: str = Header(...)):
    _require_key(x_admin_key)
    await init_db()
    return {"status": "ok", "message": "Tables created (create_all ran successfully)"}


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
