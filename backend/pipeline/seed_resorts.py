"""
Resort database seeder — idempotent upsert on slug.

Usage:
    python -m pipeline.seed_resorts                     # uses data/resorts_200.csv
    python -m pipeline.seed_resorts data/custom.csv     # uses custom CSV

CSV columns must match the resorts table schema.
"""
from __future__ import annotations

import asyncio
import csv
import sys
import uuid
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from pipeline.writer import SessionLocal
from backend.models.resort import Resort

DEFAULT_CSV = Path(__file__).parent.parent / "data" / "resorts_200.csv"


async def seed_from_csv(csv_path: str) -> None:
    path = Path(csv_path)
    if not path.exists():
        print(f"CSV file not found: {csv_path}")
        sys.exit(1)

    async with SessionLocal() as db:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
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
            print("No rows found in CSV.")
            return

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
        print(f"Upserted {len(batch)} resorts successfully.")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_CSV)
    asyncio.run(seed_from_csv(csv_path))
