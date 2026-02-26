from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.resort import Resort
from backend.schemas.responses import RegionEntry
from backend.cache import cache_get, cache_set

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionEntry])
async def list_regions(db: AsyncSession = Depends(get_db)):
    cached = await cache_get("regions:all")
    if cached:
        return cached

    stmt = (
        select(Resort.region, Resort.subregion, func.count(Resort.id).label("cnt"))
        .where(Resort.region.is_not(None))
        .group_by(Resort.region, Resort.subregion)
        .order_by(Resort.region, Resort.subregion)
    )
    rows = (await db.execute(stmt)).all()

    region_map: dict[str, dict] = {}
    for region, subregion, cnt in rows:
        if region not in region_map:
            region_map[region] = {"subregions": {}, "count": 0}
        if subregion:
            region_map[region]["subregions"][subregion] = region_map[region]["subregions"].get(subregion, 0) + cnt
        region_map[region]["count"] += cnt

    data = [
        RegionEntry(
            region=region,
            subregions=sorted(v["subregions"].keys()),
            subregion_counts=v["subregions"],
            resort_count=v["count"],
        ).model_dump()
        for region, v in sorted(region_map.items())
    ]
    await cache_set("regions:all", data, ttl_seconds=86400)
    return data
